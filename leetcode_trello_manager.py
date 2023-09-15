import logging
from datetime import datetime, timedelta
import requests
from functools import reduce
import os
import json
import configparser
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_ini_settings():
    config = configparser.ConfigParser()
    config.read('./settings.ini')

    return {
        'BASE_URL': config['TRELLO']['BASE_URL'],
        'BOARD_NAME': config['TRELLO']['BOARD_NAME'],
        'DEFAULT_LISTS': config['LISTS']['DEFAULTS'].split(', '),
        'REQUIRED_LISTS': config['LISTS']['REQUIRED'].split(', '),
        'START_DAY': int(config['WEEK']['START_DAY']),
        'END_DAY': int(config['WEEK']['END_DAY']),
        'WORKDAYS': int(config['WEEK']['WORKDAYS']),
        'DEFAULT_LABELS_COLORS': dict(item.split(':') for item in config['LABELS']['DEFAULT_COLORS'].split(', '))
    }

def load_config():
    return {
        'API_KEY': os.environ.get('API_KEY'),
        'OAUTH_TOKEN': os.environ.get('OAUTH_TOKEN'),
        'RAW_URL_BASE': os.environ.get('RAW_URL_BASE'),
        'TOPICS_JSON_PATH': os.environ.get('TOPICS_JSON_PATH')
    }

def make_request(url, method, params=None, data=None, timeout=None, files=None):
    with requests.request(method, url, params=params, data=data, timeout=timeout, files=files) as response:
        if response.status_code != 200:
            logging.error(f"Request to {url} failed with status code {response.status_code}. Response: {response.text}")
            return None
        return response.json()


def trello_request(config, settings, resource, method="GET", entity="boards", timeout=None, files=None, **kwargs):
    logging.info(f"Making a request to endpoint: {entity}/{resource}")
    url = f"{settings['BASE_URL']}/{entity}/{resource}".rstrip('/')
    query = {'key': config['API_KEY'], 'token': config['OAUTH_TOKEN'], **kwargs}
    
    return make_request(url, method, params=query, data=None, timeout=timeout, files=files)


def get_board_id(config, settings, name):
    boards = trello_request(config, settings, "me/boards", filter="open", entity="members")
    return next((board['id'] for board in boards if board['name'] == name), None)

def card_exists(config, settings, board_id, card_name):
    cards = trello_request(config, settings, f"{board_id}/cards")
    return any(card['name'] == card_name for card in cards)

def create_list(config, settings, board_id, list_name):
    return trello_request(config, settings, "", method="POST", entity="lists", idBoard=board_id, name=list_name)

def check_list_exists(config, settings, board_id, list_name):
    lists = trello_request(config, settings, f"{board_id}/lists")
    return any(lst['name'] == list_name for lst in lists)

def delete_list(config, settings, board_id, list_name):
    list_id = next(lst['id'] for lst in trello_request(config, settings, f"{board_id}/lists") if lst['name'] == list_name)
    return trello_request(config, settings, f"{list_id}/closed", method="PUT", entity="lists", value='true')

def manage_default_and_required_lists(config, settings, board_id):
    default_lists = ["To Do", "Doing", "Done"]
    required_lists = ["Completed", "Retrospective", "Do this week", "Backlog"]

    # Using list comprehension and functional style
    [delete_list(config, settings, board_id, default_list) for default_list in default_lists if check_list_exists(config, settings, board_id, default_list)]
    [create_list(config, settings, board_id, required_list) for required_list in required_lists if not check_list_exists(config, settings, board_id, required_list)]

def get_member_id(config, settings):
    response = trello_request(config, settings, "me", entity="members")
    if response is None:
        logging.error("Failed to fetch member ID.")
        return None
    return response.get('id')

def download_image(url, filepath="tmp_image.png"):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filepath, 'wb') as file:
            file.write(response.content)
        return filepath
    else:
        logging.error(f"Failed to download image. HTTP status code: {response.status_code}")
        return None

def upload_custom_board_background(config, settings, member_id, image_filepath):
    endpoint = f"members/{member_id}/customBoardBackgrounds"
    with open(image_filepath, 'rb') as file:
        files = {'file': (os.path.basename(image_filepath), file, 'image/png')}
        response = trello_request(config, settings, endpoint, method="POST", entity="", files=files)
    return response.get('id') if response else None

def set_custom_board_background(config, settings, board_id, background_id):
    endpoint = f"{board_id}/prefs/background"
    response = trello_request(config, settings, endpoint, method="PUT", entity="boards", value=background_id)
    return response if response else None



def set_board_background(config, settings, board_id):
    member_id = get_member_id(config, settings)
    if not member_id:
        logging.error("Failed to retrieve member ID")
        return

    image_filepath = download_image(f"{config['RAW_URL_BASE']}imgs/background/groot.png")
    
    if not image_filepath:
        logging.error("Failed to download image")
        return
    
    background_id = upload_custom_board_background(config, settings, member_id, image_filepath)
    if not background_id:
        logging.error("Failed to upload custom board background image")
        return
    
    response = set_custom_board_background(config, settings, board_id, background_id)
    if not response:
        logging.error("Failed to set board background image")

def generate_leetcode_link(title):
    return f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"

def compute_due_date(start_date, days):
    return reduce(lambda x, _: get_next_working_day(x) if x.weekday() < 5 else x, range(days), start_date)

def is_due_this_week(due_date, current_date):
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    return start_of_week <= due_date <= end_of_week

def attach_image_to_card(config, settings, card_id, topic):
    image_url = f"{config['RAW_URL_BASE']}imgs/cards/{topic}.png"
    response = trello_request(config, settings, f"/cards/{card_id}/attachments", "POST", url=image_url)
    if not response:
        logging.error(f"Failed to attach image to card {card_id}")

def get_next_working_day(date):
    next_day = date + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day

def generate_all_due_dates(topics, start_date):
    return reduce(lambda acc, problems: acc + [get_next_working_day(acc[-1])] * len(problems),
                  topics.values(), [get_next_working_day(start_date)])[:-1]

def create_labels_for_board(config, settings, board_id):
    label_colors = {'Easy': 'green', 'Medium': 'yellow', 'Somewhat know': 'blue', 'Do not know': 'red', 'Know': 'green'}
    labels = trello_request(config, settings, f"{board_id}/labels", entity="boards")
    if labels is None:
        logging.error(f"Failed to fetch labels for board with ID: {board_id}")
        return

    label_names = [l.get('name') for l in labels if 'name' in l]
    for label, color in label_colors.items():
        if label not in label_names:
            trello_request(config, settings, "/labels", "POST", name=label, color=color, idBoard=board_id)


def create_cards_for_board(config, settings, board_id, topics, current_date):
    list_ids_response = trello_request(config, settings, f"{board_id}/lists")
    if list_ids_response is None:
        logging.error(f"Failed to fetch lists for board with ID: {board_id}")
        return

    list_ids = {l['name']: l['id'] for l in list_ids_response}

    label_ids_response = trello_request(config, settings, f"{board_id}/labels")
    if label_ids_response is None:
        logging.error(f"Failed to fetch labels for board with ID: {board_id}")
        return

    label_ids = {l['name']: l['id'] for l in label_ids_response}
    
    all_due_dates = generate_all_due_dates(topics, current_date)
    due_date_index = 0  # Initialize due_date_index at the beginning of the function

    for idx, (category, problems) in enumerate(topics.items()):
        topic_label_response = trello_request(config, settings, "/labels", "POST", name=category, color="black", idBoard=board_id)
        if topic_label_response is None:
            logging.error(f"Failed to create label for category: {category}")
            continue

        topic_label_id = topic_label_response['id']
        for problem in problems:
            card_name = f"{category}: {problem['title']}"
            if not card_exists(config, settings, board_id, card_name):
                difficulty_label_id = label_ids.get(problem["difficulty"])
                if not difficulty_label_id:
                    logging.error(f"Difficulty label not found for problem: {problem['title']}")
                    continue

                link = generate_leetcode_link(problem["title"])                
                list_name = "Do this week" if is_due_this_week(all_due_dates[due_date_index], current_date) else "Backlog"
                due_date_for_card = all_due_dates[due_date_index]
                due_date_index += 1

                card_response = trello_request(config, settings, resource="/cards", method="POST", entity="", idList=list_ids.get(list_name), name=card_name, desc=link, idLabels=[difficulty_label_id, topic_label_id], due=due_date_for_card.isoformat())
                if not card_response:
                    logging.error(f"Failed to create card: {card_name}")
                    continue

                # Once the card is created, attach the image to the card
                attach_image_to_card(config, settings, card_response['id'], category)


def process_retrospective_cards(config, settings, board_id, current_date):
    list_ids = {l['name']: l['id'] for l in trello_request(config, settings, f"/boards/{board_id}/lists")}
    retrospective_cards = trello_request(config, settings, f"/lists/{list_ids['Retrospective']}/cards")

    for card in retrospective_cards:
        label_names = [label['name'] for label in card['labels']]
        if "Do not know" in label_names:
            new_due_date = get_next_working_day(current_date)
            list_name = "Do this week"
        elif "Somewhat know" in label_names:
            new_due_date = get_next_working_day(current_date + timedelta(weeks=1))
            list_name = "Do this week" if is_due_this_week(new_due_date, current_date) else "Backlog"
        elif "Know" in label_names:
            new_due_date = get_next_working_day(current_date + timedelta(weeks=4))
            list_name = "Completed"
        else:
            continue  # If the card doesn't have any of the expected labels, skip it

        trello_request(config, settings, f"/cards/{card['id']}", "PUT", idList=list_ids[list_name], due=new_due_date.isoformat())

def process_completed_cards(config, settings, board_id, current_date):
    list_ids = {l['name']: l['id'] for l in trello_request(config, settings, f"/boards/{board_id}/lists")}
    completed_cards = trello_request(config, settings, f"/lists/{list_ids['Completed']}/cards")
    for card in completed_cards:
        current_due_date = datetime.fromisoformat(card['due'].replace('Z', ''))
        if is_due_this_week(current_due_date, current_date):
            trello_request(config, settings, f"/cards/{card['id']}", "PUT", idList=list_ids["Do this week"])

def setup_board(config, settings,  board_name, topics, current_date):
    board_id = get_board_id(config, settings, board_name)
    if board_id is None:
        board_response = trello_request(config, settings, "", method="POST", name=board_name)
        board_id = board_response.get('id') if board_response else None

    if not board_id:
        logging.error(f"Failed to create or retrieve board with name: {board_name}")
        return

    set_board_background(config, settings, board_id)
    manage_default_and_required_lists(config, settings, board_id)
    create_labels_for_board(config, settings, board_id)
    create_cards_for_board(config, settings, board_id, topics, current_date)

    logging.info("Trello board setup completed!")

def retest_cards(config, settings, board_name, current_date):
    board_id = get_board_id(config, settings, board_name)
    process_retrospective_cards(config, settings, board_id, current_date)
    process_completed_cards(config, settings, board_id, current_date)
    logging.info("Retest cards processed!")

if __name__ == "__main__":
    config = load_config()
    settings = load_ini_settings()

    with open(config['TOPICS_JSON_PATH'], 'r') as file:
        topics = json.load(file)

    current_date = datetime.now()
    setup_board(config, settings, settings['BOARD_NAME'], topics, current_date)
    retest_cards(config, settings, settings['BOARD_NAME'], current_date)