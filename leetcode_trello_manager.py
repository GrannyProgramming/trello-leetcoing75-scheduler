import requests
import logging
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
current_date = datetime.now()
API_KEY = os.environ['API_KEY']
OAUTH_TOKEN = os.environ['OAUTH_TOKEN']
RAW_URL_BASE = os.environ['RAW_URL_BASE']
BASE_URL = "https://api.trello.com/1"
BOARD_NAME = "LeetCode Challenges"

topics = {
    "Arrays and Strings": [
        {"title": "Merge Strings Alternately", "difficulty": "Easy"},
        {"title": "Greatest Common Divisor of Strings", "difficulty": "Easy"},
        {"title": "Kids With the Greatest Number of Candies", "difficulty": "Easy"},
        {"title": "Can Place Flowers", "difficulty": "Easy"},
        {"title": "Reverse Vowels of a String", "difficulty": "Easy"},
        {"title": "Reverse Words in a String", "difficulty": "Medium"},
        {"title": "Product of Array Except Self", "difficulty": "Medium"},
        {"title": "Increasing Triplet Subsequence", "difficulty": "Medium"},
        {"title": "String Compression", "difficulty": "Medium"},
    ],
    "Two Pointers": [
        {"title": "Move Zeroes", "difficulty": "Easy"},
        {"title": "Is Subsequence", "difficulty": "Easy"},
        {"title": "Container With Most Water", "difficulty": "Medium"},
        {"title": "Max Number of K-Sum Pairs", "difficulty": "Medium"},
    ],
    "Sliding Window": [
        {"title": "Maximum Average Subarray I", "difficulty": "Easy"},
        {"title": "Maximum Number of Vowels in a Substring of Given Length", "difficulty": "Medium"},
        {"title": "Max Consecutive Ones III", "difficulty": "Medium"},
        {"title": "Longest Subarray of 1's After Deleting One Element", "difficulty": "Medium"},
    ],
    "Prefix Sum": [
        {"title": "Find the Highest Altitude", "difficulty": "Easy"},
        {"title": "Find Pivot Index", "difficulty": "Easy"},
    ],
    "Hash Map and Set": [
        {"title": "Find the Difference of Two Arrays", "difficulty": "Easy"},
        {"title": "Unique Number of Occurrences", "difficulty": "Easy"},
        {"title": "Determine if Two Strings Are Close", "difficulty": "Medium"},
        {"title": "Equal Row and Column Pairs", "difficulty": "Medium"},
    ],
    "Stack": [
        {"title": "Removing Stars From a String", "difficulty": "Medium"},
        {"title": "Asteroid Collision", "difficulty": "Medium"},
        {"title": "Decode String", "difficulty": "Medium"},
    ],
    "Queue": [
        {"title": "Number of Recent Calls", "difficulty": "Easy"},
        {"title": "Dota2 Senate", "difficulty": "Medium"},
    ],
    "Linked List": [
        {"title": "Delete the Middle Node of a Linked List", "difficulty": "Medium"},
        {"title": "Odd Even Linked List", "difficulty": "Medium"},
        {"title": "Reverse Linked List", "difficulty": "Easy"},
        {"title": "Maximum Twin Sum of a Linked List", "difficulty": "Medium"},
    ],
    "Binary Tree - DFS": [
        {"title": "Maximum Depth of Binary Tree", "difficulty": "Easy"},
        {"title": "Leaf-Similar Trees", "difficulty": "Easy"},
        {"title": "Count Good Nodes in Binary Tree", "difficulty": "Medium"},
        {"title": "Path Sum III", "difficulty": "Medium"},
        {"title": "Longest ZigZag Path in a Binary Tree", "difficulty": "Medium"},
        {"title": "Lowest Common Ancestor of a Binary Tree", "difficulty": "Medium"},
    ],
        "Binary Tree - BFS": [
        {"title": "Binary Tree Right Side View", "difficulty": "Medium"},
        {"title": "Maximum Level Sum of a Binary Tree", "difficulty": "Medium"},
    ],
    "Binary Search Tree": [
        {"title": "Search in a Binary Search Tree", "difficulty": "Easy"},
        {"title": "Delete Node in a BST", "difficulty": "Medium"},
    ],
    "Graphs - DFS": [
        {"title": "Keys and Rooms", "difficulty": "Medium"},
        {"title": "Number of Provinces", "difficulty": "Medium"},
        {"title": "Reorder Routes to Make All Paths Lead to the City Zero", "difficulty": "Medium"},
        {"title": "Evaluate Division", "difficulty": "Medium"},
    ],
    "Graphs - BFS": [
        {"title": "Nearest Exit from Entrance in Maze", "difficulty": "Medium"},
        {"title": "Rotting Oranges", "difficulty": "Medium"},
    ],
    "Heap and Priority Queue": [
        {"title": "Kth Largest Element in an Array", "difficulty": "Medium"},
        {"title": "Smallest Number in Infinite Set", "difficulty": "Medium"},
        {"title": "Maximum Subsequence Score", "difficulty": "Medium"},
        {"title": "Total Cost to Hire K Workers", "difficulty": "Medium"},
    ],
    "Binary Search": [
        {"title": "Guess Number Higher or Lower", "difficulty": "Easy"},
        {"title": "Successful Pairs of Spells and Potions", "difficulty": "Medium"},
        {"title": "Find Peak Element", "difficulty": "Medium"},
        {"title": "Koko Eating Bananas", "difficulty": "Medium"},
    ],
    "Backtracking": [
        {"title": "Letter Combinations of a Phone Number", "difficulty": "Medium"},
        {"title": "Combination Sum III", "difficulty": "Medium"},
    ],
    "DP - 1D": [
        {"title": "N-th Tribonacci Number", "difficulty": "Easy"},
        {"title": "Min Cost Climbing Stairs", "difficulty": "Easy"},
        {"title": "House Robber", "difficulty": "Medium"},
        {"title": "Domino and Tromino Tiling", "difficulty": "Medium"},
    ],
    "DP - Multidimensional": [
        {"title": "Unique Paths", "difficulty": "Medium"},
        {"title": "Longest Common Subsequence", "difficulty": "Medium"},
        {"title": "Best Time to Buy and Sell Stock with Transaction Fee", "difficulty": "Medium"},
        {"title": "Edit Distance", "difficulty": "Medium"},
    ],
    "Bit Manipulation": [
        {"title": "Counting Bits", "difficulty": "Easy"},
        {"title": "Single Number", "difficulty": "Easy"},
        {"title": "Minimum Flips to Make a OR b Equal to c", "difficulty": "Medium"},
    ],
    "Trie": [
        {"title": "Implement Trie (Prefix Tree)", "difficulty": "Medium"},
        {"title": "Search Suggestions System", "difficulty": "Medium"},
    ],
    "Intervals": [
        {"title": "Non-overlapping Intervals", "difficulty": "Medium"},
        {"title": "Minimum Number of Arrows to Burst Balloons", "difficulty": "Medium"},
    ],
    "Monotonic Stack": [
        {"title": "Daily Temperatures", "difficulty": "Medium"},
        {"title": "Online Stock Span", "difficulty": "Medium"},
    ],
}

def request_trello(endpoint, method="GET", **kwargs):
    logging.info(f"Making a request to endpoint: {endpoint}")
    url = f"{BASE_URL}{endpoint}"
    query = {'key': API_KEY, 'token': OAUTH_TOKEN, **kwargs}
    response = requests.request(method, url, params=query)
    if response.status_code != 200:
        logging.error(f"Request failed with status code {response.status_code}: {response.text}")
        return None  # or you can raise an exception based on your requirement
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return None

def card_exists(board_id, card_name):
    """Check if a card with the given name exists on the board."""
    cards = request_trello(f"/boards/{board_id}/cards")
    return any(card['name'] == card_name for card in cards)

def set_board_background(board_id):
    background_img_url = f"{RAW_URL_BASE}imgs/backgrounds/groot.png"
    response = request_trello(f"/boards/{board_id}/prefs/backgroundImage", "PUT", value=background_img_url)
    if not response:
        logging.error("Failed to set board background image")

def attach_image_to_card(card_id, topic):
    image_url = f"{RAW_URL_BASE}imgs/cards/{topic}.png"
    response = request_trello(f"/cards/{card_id}/attachments", "POST", url=image_url)
    if not response:
        logging.error(f"Failed to attach image to card {card_id}")
        
def get_board_id(name):
    return next((board['id'] for board in request_trello("/members/me/boards", filter="open") if board['name'] == name), None)

def generate_leetcode_link(title):
    return f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"

def compute_due_date(start_date, days):
    due_date = start_date
    while days > 0:
        due_date += timedelta(days=1)
        if due_date.weekday() < 5:
            days -= 1
    return due_date

def is_due_this_week(due_date):
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    return start_of_week <= due_date <= end_of_week

def get_next_working_day(date):
    next_day = date + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day

def generate_all_due_dates(topics, start_date):
    due_dates = []
    next_due_date = get_next_working_day(start_date)
    for topic, problems in topics.items():
        for _ in problems:
            due_dates.append(next_due_date)
            next_due_date = get_next_working_day(next_due_date)
    return due_dates

def retest_cards(board_name):
    # Retrieve all cards from the Retrospective and Completed lists
    board_id = get_board_id(board_name)
    list_ids = {l['name']: l['id'] for l in request_trello(f"/boards/{board_id}/lists")}
    retrospective_cards = request_trello(f"/lists/{list_ids['Retrospective']}/cards")
    completed_cards = request_trello(f"/lists/{list_ids['Completed']}/cards")

    # Process cards from the Retrospective list
    for card in retrospective_cards:
        label_names = [label['name'] for label in card['labels']]
        if "Do not know" in label_names:
            new_due_date = get_next_working_day(current_date)
            list_name = "Do this week"
        elif "Somewhat know" in label_names:
            new_due_date = get_next_working_day(current_date + timedelta(weeks=1))
            list_name = "Do this week" if is_due_this_week(new_due_date) else "Backlog"
        elif "Know" in label_names:
            new_due_date = get_next_working_day(current_date + timedelta(weeks=4))
            list_name = "Completed"
        else:
            continue  # If the card doesn't have any of the expected labels, skip it

        # Move card to the correct list based on its recalculated due date
        request_trello(f"/cards/{card['id']}", "PUT", idList=list_ids[list_name], due=new_due_date.isoformat())

    # Process cards from the Completed list
    for card in completed_cards:
        current_due_date = datetime.fromisoformat(card['due'].replace('Z', ''))
        if is_due_this_week(current_due_date):
            # Move card to the "Do this week" list without changing its due date
            request_trello(f"/cards/{card['id']}", "PUT", idList=list_ids["Do this week"])

    logging.info("Retest cards processed!")

def setup_board(board_name, topics):
    board_id = get_board_id(board_name) or request_trello("/boards", "POST", name=board_name)['id']
    set_board_background(board_id)  # Setting the board background image
    existing_list_names = {lst['name'] for lst in request_trello(f"/boards/{board_id}/lists", cards="none")}
    
    # Delete default lists
    for default_list in ["To Do", "Doing", "Done"]:
        if default_list in existing_list_names:
            list_id = next(lst['id'] for lst in request_trello(f"/boards/{board_id}/lists", cards="none") if lst['name'] == default_list)
            request_trello(f"/lists/{list_id}/closed", "PUT", value='true')

    # Create required lists
    for required_list in ["Completed", "Retrospective", "Do this week", "Backlog"]:
        if required_list not in existing_list_names:
            response = request_trello("/lists", "POST", idBoard=board_id, name=required_list)

    list_ids = {l['name']: l['id'] for l in request_trello(f"/boards/{board_id}/lists")}
    label_colors = {'Easy': 'green', 'Medium': 'yellow', 'Somewhat know': 'blue', 'Do not know': 'red', 'Know': 'green'}
    
    for label, color in label_colors.items():
        labels = request_trello(f"/boards/{board_id}/labels")
        if label not in [l['name'] for l in labels]:
            request_trello("/labels", "POST", name=label, color=color, idBoard=board_id)
    
    label_ids = {l['name']: l['id'] for l in request_trello(f"/boards/{board_id}/labels")}
    all_due_dates = generate_all_due_dates(topics, current_date)
    due_date_index = 0  # Initialize due_date_index at the beginning of the function

    for category, problems in topics.items():
        topic_label_id = request_trello("/labels", "POST", name=category, color="black", idBoard=board_id)['id']
        for problem in problems:
            card_name = f"{category}: {problem['title']}"
            if not card_exists(board_id, card_name):
                difficulty_label_id = label_ids[problem["difficulty"]]
                link = generate_leetcode_link(problem["title"])                
                list_name = "Do this week" if is_due_this_week(all_due_dates[due_date_index]) else "Backlog"
                due_date_for_card = all_due_dates[due_date_index]
                due_date_index += 1
                card_response = request_trello("/cards", "POST", idList=list_ids[list_name], name=card_name, desc=link, idLabels=[difficulty_label_id, topic_label_id], due=due_date_for_card.isoformat())
                # Once the card is created, attach the image to the card
                if card_response:
                    attach_image_to_card(card_response['id'], category)

    logging.info("Trello board setup completed!")

setup_board(BOARD_NAME, topics)
retest_cards(BOARD_NAME)