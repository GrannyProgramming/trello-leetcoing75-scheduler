"""
Trello Card Management Module.

This module provides utility functions to manage Trello cards with specific operations such as:
- Fetching all list and label IDs for a given board
- Attaching an image to a card
- Creating labels for topics
- Processing single and all problem cards
- Retesting cards and processing retrospective and completed cards
- Determining new due dates and lists based on card labels

The module heavily leverages the Trello API to perform these operations.

Constants:
    TRELLO_ENTITY (dict): Dictionary mapping entity names to their corresponding Trello API endpoints.

Dependencies:
    - logging: Used for logging information and error messages.
    - datetime: Used for date manipulations.
    - .trello_api: Module containing base functions for Trello API interactions.
    - .utilities: Module containing utility functions for various operations.

Functions:
    - fetch_all_list_ids: Retrieve all list IDs for a given board.
    - fetch_all_label_ids: Retrieve all label IDs for a given board.
    - attach_image_to_card: Attach an image to a specified card.
    - create_topic_label: Create a label for a particular topic on Trello.
    - process_single_problem_card: Process a single problem card for insertion to Trello.
    - process_all_problem_cards: Process all problem cards for a board.
    - retest_cards: Process retest cards for a given board.
    - determine_new_due_date_and_list: Determine the new due date and list for a card based on its labels.
    - parse_card_due_date: Parse the 'due' date of a card into a datetime object.
    - process_retrospective_cards: Process cards in the 'Retrospective' list.
    - process_completed_cards: Process cards in the 'Completed' list based on their due dates.

Note:
    Ensure the required Trello API credentials are available and the necessary modules are imported when calling functions from this module.

Author: Alex McGonigle @grannyprogramming
"""


import logging
from datetime import datetime, timedelta
from .trello_api import trello_request, card_exists, get_board_id, fetch_cards_from_list
from .utilities import (
    generate_leetcode_link,
    get_list_name_and_due_date,
    generate_all_due_dates,
    is_due_this_week,
    get_next_working_day
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def fetch_all_list_ids(config, settings, board_id):
    """Retrieve all list IDs for a given board."""
    response = trello_request(config, settings, "lists", entity="boards", board_id=board_id)
    if response is None:
        logging.error("Failed to fetch lists for board with ID: %s", board_id)
        return {}
    return {l["name"]: l["id"] for l in response}


def fetch_all_label_ids(config, settings, board_id):
    """Retrieve all label IDs for a given board."""
    response = trello_request(config, settings, "labels", entity="boards", board_id=board_id)
    if response is None:
        logging.error("Failed to fetch labels for board with ID: %s", board_id)
        return {}
    return {l["name"]: l["id"] for l in response}


def attach_image_to_card(config, settings, card_id, topic):
    """Attach an image to a given card."""
    image_url = f"{config['RAW_URL_BASE']}imgs/cards/{topic}.png"
    response = trello_request(
        config,
        settings,
        f"{card_id}/attachments",
        "POST",
        entity="cards",
        url=image_url,
    )
    if not response:
        logging.error("Failed to attach image to card %s", card_id)


def create_topic_label(config, settings, board_id, category):
    """Create a label for a given topic."""
    return trello_request(
        config,
        settings,
        "/labels",
        "POST",
        entity="boards",
        board_id=board_id,
        name=category,
        color="black",
    )


def process_single_problem_card(
    config,
    settings,
    board_id,
    list_ids,
    label_ids,
    topic_label_id,
    category,
    problem,
    due_date,
    current_date,
):
    """
    Create a Trello card for a single LeetCode problem.
    """
    card_name = f"{category}: {problem['title']}"
    if not card_exists(config, settings, board_id, card_name):
        difficulty_label_id = label_ids.get(problem["difficulty"])
        if not difficulty_label_id:
            logging.error(
                "Difficulty label not found for problem: %s", problem["title"]
            )
            return
        link = generate_leetcode_link(problem["title"])
        list_name, due_date_for_card = get_list_name_and_due_date(
            due_date, current_date
        )
        card_response = trello_request(
            config,
            settings,
            resource="/cards",
            method="POST",
            entity="",
            idList=list_ids.get(list_name),
            name=card_name,
            desc=link,
            idLabels=[difficulty_label_id, topic_label_id],
            due=due_date_for_card.isoformat(),
        )
        if not card_response:
            logging.error("Failed to create card: %s", card_name)
            return
        attach_image_to_card(config, settings, card_response["id"], category)


def process_all_problem_cards(config, settings, board_id, topics, current_date):
    """Process all problem cards for a given board."""
    list_ids = fetch_all_list_ids(config, settings, board_id)
    label_ids = fetch_all_label_ids(config, settings, board_id)
    all_due_dates = generate_all_due_dates(topics, current_date, settings["PROBLEMS_PER_DAY"])
    due_date_index = 0

    for category, problems in topics.items():
        topic_label_response = create_topic_label(config, settings, board_id, category)
        if topic_label_response is None:
            logging.error("Failed to create label for category: %s", category)
            continue
        topic_label_id = topic_label_response["id"]
        for problem in problems:
            process_single_problem_card(
                config,
                settings,
                board_id,
                list_ids,
                label_ids,
                topic_label_id,
                category,
                problem,
                all_due_dates[due_date_index],
                current_date,
            )
            due_date_index += 1


def retest_cards(config, settings, board_name, current_date):
    """Process retest cards for a given board."""
    board_id = get_board_id(config, settings, board_name)
    process_retrospective_cards(config, settings, board_id, current_date)
    process_completed_cards(config, settings, board_id, current_date)
    logging.info("Retest cards processed!")


def determine_new_due_date_and_list(label_names, current_date):
    """Determine the new due date and list based on labels."""
    if "Do not know" in label_names:
        new_due_date = get_next_working_day(current_date)
        return new_due_date, "Do this week"
    elif "Somewhat know" in label_names:
        new_due_date = get_next_working_day(current_date + timedelta(weeks=1))
        list_name = (
            "Do this week"
            if is_due_this_week(new_due_date, current_date)
            else "Backlog"
        )
        return new_due_date, list_name
    elif "Know" in label_names:
        new_due_date = get_next_working_day(current_date + timedelta(weeks=4))
        return new_due_date, "Completed"
    return None, None


def parse_card_due_date(card_due):
    """Parse the 'due' date of a card into a datetime object."""
    return datetime.fromisoformat(card_due.replace("Z", ""))


def filter_cards_by_label(cards):
    """Filter out cards with specific labels."""
    if not cards:
        return []

    return [
        card for card in cards if not set(["Somewhat know", "Do not know", "Know"]) & set(card["labels"])
    ]


def apply_changes_to_board(config, settings, list_ids, cards_to_add):
    """Apply the necessary changes to the Trello board (like pulling cards from backlog)."""
    to_do_this_week_id = list_ids.get("To Do this Week")
    
    for _ in range(cards_to_add):
        top_card = get_top_card_from_backlog(config, settings, list_ids)
        if top_card:
            move_card_to_list(config, settings, top_card['id'], to_do_this_week_id)
        else:
            logging.warning("No more cards to pull from the 'Backlog'.")
            break

def get_top_card_from_backlog(config, settings, list_ids):
    """
    Get the top card from the 'Backlog' list.
    """
    backlog_id = list_ids.get("Backlog")
    backlog_cards = fetch_cards_from_list(config, settings, backlog_id)
    if not backlog_cards:
        logging.warning("No cards found in the 'Backlog' list.")
        return None
    return backlog_cards[0]

def move_card_to_list(config, settings, card_id, target_list_id):
    """
    Move a card to a specified list.
    """
    trello_request(
        config,
        settings,
        card_id,  # Just use the card_id as the resource.
        "PUT",
        entity="cards",  # Explicitly mention the entity here.
        idList=target_list_id
    )
    logging.info("Moved card with ID %s to list with ID %s.", card_id, target_list_id)


def process_retrospective_cards(config, settings, board_id, current_date):
    """Process the retrospective cards."""
    list_ids = fetch_all_list_ids(config, settings, board_id)
    retrospective_cards = trello_request(
        config, settings, "cards", entity="lists", list_id=list_ids['Retrospective']
    )


    if retrospective_cards:
        for card in retrospective_cards:
            label_names = [label["name"] for label in card["labels"]]
            new_due_date, list_name = determine_new_due_date_and_list(
                label_names, current_date
            )
            if not list_name:
                continue
            trello_request(
                config,
                settings,
                f"/cards/{card['id']}",
                "PUT",
                idList=list_ids[list_name],
                due=new_due_date.isoformat(),
            )


def process_completed_cards(config, settings, board_id, current_date):
    """Move completed cards that are due this week to the 'Do this week' list."""
    list_ids = fetch_all_list_ids(config, settings, board_id)
    completed_cards = trello_request(
        config, settings, "cards", entity="lists", list_id=list_ids["Completed"]
    )

    for card in completed_cards:
        if is_due_this_week(parse_card_due_date(card["due"]), current_date):
            trello_request(
                config,
                settings,
                f"/cards/{card['id']}",
                "PUT",
                idList=list_ids["Do this week"],
            )
