"""
Trello Card Management Module.

This module provides utility functions for managing various aspects of Trello cards.
It supports operations such as checking if a card exists, filtering cards based on labels, 
applying changes to cards, moving cards between lists, processing retrospective and completed cards, 
and more.

Functions:
    - card_exists(_config, _settings, board_id, card_name): Checks if a card exists on a specified board.
    - filter_cards_by_label(cards, _settings): Filters out cards with specific labels defined in _settings.
    - apply_changes_to_cards(_config, _settings, list_ids, cards_to_add): Applies changes to Trello cards, 
      especially for managing the "Do this week" list.
    - get_top_card_from_backlog(_config, _settings, list_ids): Retrieves the top card from the 'Backlog' list.
    - move_card_to_list(_config, _settings, card_id, target_list_id): Moves a card to a specified list.
    - process_retrospective_cards(_config, _settings, board_id, current_date): Processes the retrospective 
      cards based on their labels and due dates.
    - process_completed_cards(_config, _settings, board_id, current_date): Moves completed cards that are due 
      this week to the 'Do this week' list.
    - attach_image_to_card(_config, _settings, card_id, topic): Attaches an image to a specified card.
    - create_topic_label(_config, _settings, board_id, category): Creates a label for a given topic.
    - retest_cards(_config, _settings, board_name, current_date): Processes retest cards for a specified board.
    - manage_this_week_list(__config, __settings, board_id): Ensures the 'To Do this Week' list has the
      required number of cards.
    - get_max_cards_for_week(_settings): Calculates the maximum number of cards required for the week.
    - fetch_cards_from_list(_config, _settings, list_id): Fetches all cards from a given list.
    - process_single_problem_card(_config, _settings, board_id, list_ids, label_ids, topic_label_id, category, problem, due_date, current_date): Creates a Trello card for a single LeetCode problem.
    - process_all_problem_cards(_config, _settings, board_id, topics, current_date): Processes all problem cards for a given board.
    - add_comment_to_card(_config, _settings, card_id, comment_content): Adds a comment to a given card.

Dependencies:
    - logging: Used for logging information and error messages.
    - .trello_api: Houses Trello-specific API functions.
    - .board_operations: Provides functions for board-related operations.
    - .utilities: Contains utility functions related to date parsing and filtering.

Author: Alex McGonigle @grannyprogramming
"""


import logging
from .trello_api import trello_request
from .board_operations import fetch_all_list_ids, get_board_id, fetch_all_label_ids
from .utilities import (
    determine_new_due_date_and_list,
    parse_card_due_date,
    is_due_this_week,
    generate_leetcode_link,
    generate_all_due_dates,
    get_list_name_and_due_date,
    load_comment_from_md_file,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def card_exists(_config, _settings, board_id, card_name):
    """Check if a card exists on the board."""
    cards = trello_request(_config, _settings, f"{board_id}/cards")
    return any(card["name"] == card_name for card in cards)


def filter_cards_by_label(cards, _settings):
    """Filter out cards with specific labels."""
    if not cards:
        return []

    # Extracting the label names from the _settings without considering the colors
    exclude_labels = set(
        label_name
        for label_name, _ in _settings["DEFAULT_LABELS_COLORS"].items()
        if label_name in ["Somewhat know", "Do not know", "Know"]
    )

    # Filter out cards that have any of the excluded labels
    return [
        card
        for card in cards
        if not exclude_labels & {label["name"] for label in card["labels"]}
    ]


def apply_changes_to_cards(_config, _settings, list_ids, cards_to_add):
    """Apply the necessary changes to the Trello cards (like pulling cards from backlog)."""
    to_do_this_week_id = list_ids.get("Do this week")
    if not to_do_this_week_id:
        logging.error("To Do this Week ID not found when trying to apply changes.")
        return

    # Fetch the current cards in the "Do this week" list.
    current_cards = fetch_cards_from_list(_config, _settings, to_do_this_week_id)
    if not current_cards:
        current_cards = []

    # Filter out the cards that have the labels "Somewhat know:blue", "Do not know:red", and "Know:green".
    filtered_cards = filter_cards_by_label(current_cards, _settings)

    # Calculate how many more cards are needed in the "Do this week" list to meet the weekly quota.
    cards_needed = get_max_cards_for_week(_settings) - len(filtered_cards)
    cards_to_pull = min(cards_needed, cards_to_add)

    for _ in range(cards_to_pull):
        top_card = get_top_card_from_backlog(_config, _settings, list_ids)
        if top_card:
            move_card_to_list(_config, _settings, top_card["id"], to_do_this_week_id)
        else:
            logging.warning("No more cards to pull from the 'Backlog'.")
            break


def get_top_card_from_backlog(_config, _settings, list_ids):
    """
    Get the top card from the 'Backlog' list.
    """
    backlog_id = list_ids.get("Backlog")
    if not backlog_id:
        logging.error("Backlog ID not found when trying to get the top card.")
        return None
    backlog_cards = fetch_cards_from_list(_config, _settings, backlog_id)
    if not backlog_cards:
        logging.warning("No cards found in the 'Backlog' list.")
        return None
    return backlog_cards[0]


def move_card_to_list(_config, _settings, card_id, target_list_id):
    """
    Move a card to a specified list.
    """
    trello_request(
        _config,
        _settings,
        card_id,  # Just use the card_id as the resource.
        "PUT",
        entity="cards",  # Explicitly mention the entity here.
        idList=target_list_id,
    )
    logging.info("Moved card with ID %s to list with ID %s.", card_id, target_list_id)


def process_retrospective_cards(_config, _settings, board_id, current_date):
    """Process the retrospective cards."""
    list_ids = fetch_all_list_ids(_config, _settings, board_id)
    retrospective_list_name = _settings["REQUIRED_LISTS"][1]  # "Retrospective"
    retrospective_cards = trello_request(
        _config,
        _settings,
        "cards",
        entity="lists",
        list_id=list_ids[retrospective_list_name],
    )

    if retrospective_cards:
        for card in retrospective_cards:
            label_names = [label["name"] for label in card["labels"]]
            new_due_date, list_name = determine_new_due_date_and_list(
                label_names, current_date
            )
            if not list_name:
                continue

            # Update the card's list and due date
            trello_request(
                _config,
                _settings,
                card["id"],
                "PUT",
                entity="cards",
                idList=list_ids[list_name],
                due=new_due_date.isoformat(),
            )


def process_completed_cards(_config, _settings, board_id, current_date):
    """Move completed cards that are due this week to the 'Do this week' list."""
    list_ids = fetch_all_list_ids(_config, _settings, board_id)
    completed_list_name = _settings["REQUIRED_LISTS"][
        0
    ]  # Assuming "Completed" is the first item in REQUIRED_LISTS
    completed_cards = trello_request(
        _config,
        _settings,
        "cards",
        entity="lists",
        list_id=list_ids[completed_list_name],
    )

    for card in completed_cards:
        if is_due_this_week(parse_card_due_date(card["due"]), current_date):
            trello_request(
                _config,
                _settings,
                f"/cards/{card['id']}",
                "PUT",
                idList=list_ids["Do this week"],
            )


def attach_image_to_card(_config, _settings, card_id, topic):
    """Attach an image to a given card."""
    image_url = f"{_config['RAW_URL_BASE']}imgs/cards/{topic}.png"
    response = trello_request(
        _config,
        _settings,
        f"{card_id}/attachments",
        "POST",
        entity="cards",
        url=image_url,
    )
    if not response:
        logging.error("Failed to attach image to card %s", card_id)


def create_topic_label(_config, _settings, board_id, category):
    """Create a label for a given topic."""
    return trello_request(
        _config,
        _settings,
        "/labels",
        "POST",
        entity="boards",
        board_id=board_id,
        name=category,
        color="black",
    )


def retest_cards(_config, _settings, board_name, current_date):
    """Process retest cards for a given board."""
    board_id = get_board_id(_config, _settings, board_name)
    process_retrospective_cards(_config, _settings, board_id, current_date)
    process_completed_cards(_config, _settings, board_id, current_date)
    logging.info("Retest cards processed!")


def manage_this_week_list(__config, __settings, board_id):
    """
    Ensure the 'To Do this Week' list has the required number of cards based on the _settings.
    Cards with specific labels are excluded from this count.
    """
    max_cards = get_max_cards_for_week(__settings)

    # Fetch list IDs and get the ID for "To Do this Week"
    list_ids = fetch_all_list_ids(__config, __settings, board_id)
    to_do_this_week_name = __settings["REQUIRED_LISTS"][2]
    to_do_this_week_id = list_ids.get(to_do_this_week_name)

    # Fetch and filter cards
    cards = fetch_cards_from_list(__config, __settings, to_do_this_week_id)
    filtered_cards = filter_cards_by_label(cards, __settings)

    logging.info("Max cards for the week: %s", max_cards)
    logging.info(
        "Number of filtered cards in 'To Do this Week' list: %s", len(filtered_cards)
    )

    # Calculate the number of cards to pull
    cards_to_pull_count = max_cards - len(filtered_cards)

    logging.info("Need to pull %s cards to meet the weekly quota.", cards_to_pull_count)

    apply_changes_to_cards(__config, __settings, list_ids, cards_to_pull_count)


def get_max_cards_for_week(_settings):
    """Calculate maximum cards for the week."""
    return _settings["PROBLEMS_PER_DAY"] * _settings["WORKDAYS"]


def fetch_cards_from_list(_config, _settings, list_id):
    """Fetch all cards from a given list."""
    logging.debug("Fetching cards for list_id: %s", list_id)
    if not list_id:
        logging.error("list_id is not provided when trying to fetch cards from a list.")
        return None
    return trello_request(_config, _settings, "cards", entity="lists", list_id=list_id)


def add_comment_to_card(_config, _settings, card_id, comment_content):
    """Add a comment to a given card."""
    response = trello_request(
        _config,
        _settings,
        f"{card_id}/actions/comments",
        "POST",
        entity="cards",
        text=comment_content,
    )
    if not response:
        logging.error("Failed to add comment to card %s", card_id)


def process_single_problem_card(
    _config,
    _settings,
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
    if not card_exists(_config, _settings, board_id, card_name):
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
            _config,
            _settings,
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
        attach_image_to_card(_config, _settings, card_response["id"], category)
        comment_md_content = load_comment_from_md_file(_settings["COMMENT_MD_PATH"])
        add_comment_to_card(_config, _settings, card_response["id"], comment_md_content)


def process_all_problem_cards(_config, _settings, board_id, topics, current_date):
    """Process all problem cards for a given board."""
    list_ids = fetch_all_list_ids(_config, _settings, board_id)
    label_ids = fetch_all_label_ids(_config, _settings, board_id)
    all_due_dates = generate_all_due_dates(
        topics, current_date, _settings["PROBLEMS_PER_DAY"]
    )
    due_date_index = 0

    for category, problems in topics.items():
        topic_label_response = create_topic_label(
            _config, _settings, board_id, category
        )
        if topic_label_response is None:
            logging.error("Failed to create label for category: %s", category)
            continue
        topic_label_id = topic_label_response["id"]
        for problem in problems:
            process_single_problem_card(
                _config,
                _settings,
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
