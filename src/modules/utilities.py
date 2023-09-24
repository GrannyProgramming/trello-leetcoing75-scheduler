"""
Utilities for LeetCode Trello Automation.

This module provides utility functions designed to support operations related to automating
LeetCode tasks on Trello. The utilities range from generating LeetCode links, computing 
due dates, checking if a task is due in the current week, downloading images from URLs,
identifying the next working day, and more.

Functions:
    - generate_leetcode_link: Constructs a URL link for a given LeetCode problem title.
    - compute_due_date: Calculates the due date based on a start date and a given number of days, considering working days.
    - is_due_this_week: Checks if a specified due date falls within the current week.
    - download_image: Downloads an image from a given URL and saves it to a specified filepath.
    - get_next_working_day: Identifies the next working day after a given date.
    - generate_all_due_dates: Generates a list of due dates for a given set of topics, starting from a specified date.
    - get_list_name_and_due_date: Determines the appropriate list name (e.g., 'Do this week' or 'Backlog') for a given due date.

Dependencies:
    - logging: Used for logging information and error messages.
    - requests: Used to send HTTP requests and download content.
    - datetime: Used for date and time-related operations.
    - functools: Used for higher-order functions and operations on callable objects.

Note:
    Ensure that when using the `download_image` function, you have permission to access and download the content from the specified URL.

Author: Alex McGonigle @grannyprogramming
"""

import logging
from datetime import timedelta
import requests


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def generate_leetcode_link(title):
    """Generate a direct LeetCode problem link based on its title."""
    return f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"


def is_due_this_week(due_date, current_date):
    """Determine if a given due date falls within the current week."""
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    return start_of_week <= due_date <= end_of_week



def construct_url(base_url, entity, resource, **kwargs):
    """
    Construct the URL by joining base_url, entity, board_id (if provided), list_id (if provided), and resource.
    Ensure that there are no double slashes.
    """
    # Prepare a list to hold all components of the URL.
    url_components = [base_url.rstrip('/')]  # Ensure base_url doesn't end with a slash
    
    # Add the entity
    url_components.append(entity)
    
    # If board_id is provided, add it
    if 'board_id' in kwargs and kwargs['board_id']:
        url_components.append(kwargs['board_id'])
    
    # If list_id is provided, add it
    if 'list_id' in kwargs and kwargs['list_id']:
        url_components.append(kwargs['list_id'])
    
    # If card_id is provided, add it
    if 'card_id' in kwargs and kwargs['card_id']:
        url_components.append(kwargs['card_id'])
    
    # Add the resource without any leading slash
    url_components.append(resource.lstrip('/'))
    
    # Debug logs to identify the issue
    logging.debug("URL Components before cleaning: %s", url_components)
    
    # Filter out None or empty components and join them with '/'
    cleaned_url = '/'.join(filter(None, url_components))
    
    logging.debug("Constructed URL: %s", cleaned_url)
    return cleaned_url





def download_image(url, filepath="tmp_image.png"):
    """Download an image from a given URL and save it to a specified path."""
    try:
        response = requests.get(url, timeout=10)  # Added timeout of 10 seconds
        if response.status_code == 200:
            with open(filepath, "wb") as file:
                file.write(response.content)
            return filepath
        else:
            logging.error(
                "Failed to download image. HTTP status code: %s", response.status_code
            )
            return None
    except requests.Timeout:
        logging.error("Request to %s timed out.", url)
        return None


def get_next_working_day(date):
    """Get the next working day after a given date, skipping weekends."""
    next_day = date + timedelta(days=1)
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += timedelta(days=1)
    return next_day


def generate_all_due_dates(topics, current_date, problems_per_day):
    """Generate due dates for every problem, considering weekdays."""
    due_dates = []
    total_problems = sum(len(problems) for problems in topics.values())
    day = current_date
    
    while len(due_dates) < total_problems: # While loop to ensure all problems get a due date
        if day.weekday() < 5:  # 0-4 denotes Monday to Friday
            for _ in range(min(problems_per_day, total_problems - len(due_dates))): # Ensure we don't overshoot the total problems
                due_dates.append(day)
            day += timedelta(days=1)
        else:
            day += timedelta(days=1) # Increment the day even if it's a weekend

    return due_dates


def get_list_name_and_due_date(due_date, current_date):
    """Determine the appropriate list name and due date based on the current date."""
    list_name = (
        "Do this week" if is_due_this_week(due_date, current_date) else "Backlog"
    )
    return list_name, due_date

def get_max_cards_for_week(settings):
    """Calculate maximum cards for the week."""
    return settings["PROBLEMS_PER_DAY"] * settings["WORKDAYS"]
