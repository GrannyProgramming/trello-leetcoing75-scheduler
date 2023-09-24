"""
LeetCode Trello Utilities Module.

This module offers utility functions tailored for managing LeetCode problem cards on Trello.
It facilitates operations such as processing single or multiple problem cards, determining due dates, 
parsing and managing dates, and more.

Functions:
    - generate_leetcode_link(title): Generates a direct link to a LeetCode problem based on its title.
    - process_single_problem_card(_config, _settings, board_id, list_ids, label_ids, topic_label_id, category, problem, due_date, current_date): Creates a Trello card for a single LeetCode problem.
    - process_all_problem_cards(_config, _settings, board_id, topics, current_date): Processes all problem cards for a given board.
    - generate_all_due_dates(topics, current_date, problems_per_day): Generates due dates for every problem, taking into account weekdays.
    - get_list_name_and_due_date(due_date, current_date): Determines the appropriate list name and due date based on the current date.
    - is_due_this_week(due_date, current_date): Checks if a specified due date falls within the current week.
    - get_next_working_day(date): Returns the next working day after a given date, excluding weekends.
    - get_max_cards_for_week(_settings): Calculates the maximum number of cards for the week.
    - determine_new_due_date_and_list(label_names, current_date): Determines the new due date and list for a card based on its labels.
    - parse_card_due_date(card_due): Parses the 'due' date of a card into a datetime object.

Dependencies:
    - logging: Used for logging information and error messages.
    - datetime: Used for date operations and manipulations.
    - .card_operations: Contains utility functions related to card operations.
    - .trello_api: Houses Trello-specific API functions.
    - .board_operations: Provides functions for board-related operations.

Author: Alex McGonigle @grannyprogramming
"""


import logging
from datetime import timedelta, datetime
from .card_operations import card_exists, attach_image_to_card, create_topic_label
from .trello_api import trello_request
from .board_operations import fetch_all_list_ids, fetch_all_label_ids

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def generate_leetcode_link(title):
    """Generate a direct LeetCode problem link based on its title."""
    return f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"


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


def generate_all_due_dates(topics, current_date, problems_per_day):
    """Generate due dates for every problem, considering weekdays."""
    due_dates = []
    total_problems = sum(len(problems) for problems in topics.values())
    day = current_date

    while (
        len(due_dates) < total_problems
    ):  # While loop to ensure all problems get a due date
        if day.weekday() < 5:  # 0-4 denotes Monday to Friday
            for _ in range(
                min(problems_per_day, total_problems - len(due_dates))
            ):  # Ensure we don't overshoot the total problems
                due_dates.append(day)
            day += timedelta(days=1)
        else:
            day += timedelta(days=1)  # Increment the day even if it's a weekend

    return due_dates


def get_list_name_and_due_date(due_date, current_date):
    """Determine the appropriate list name and due date based on the current date."""
    list_name = (
        "Do this week" if is_due_this_week(due_date, current_date) else "Backlog"
    )
    return list_name, due_date


def is_due_this_week(due_date, current_date):
    """Determine if a given due date falls within the current week."""
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    return start_of_week <= due_date <= end_of_week


def get_next_working_day(date):
    """Get the next working day after a given date, skipping weekends."""
    next_day = date + timedelta(days=1)
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += timedelta(days=1)
    return next_day


def get_max_cards_for_week(_settings):
    """Calculate maximum cards for the week."""
    return _settings["PROBLEMS_PER_DAY"] * _settings["WORKDAYS"]


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
