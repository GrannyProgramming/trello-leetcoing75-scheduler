"""
Main script for Trello Card Management.

This script coordinates the primary operations for managing Trello cards, including setting up the Trello board, 
processing LeetCode problems, and managing card retests. The script leverages various utility functions from 
imported modules for specific tasks.

Functions:
    - setup_trello_board: Set up the Trello board by ensuring the necessary lists and labels exist.
    - process_cards: Process all problem cards for the board, populate the "To Do this Week" list, and manage card retests.
    - main: The main function that coordinates the primary operations.

Usage:
    This script is intended to be run as the main entry point. It should be executed after the necessary environment 
    variables and configurations are set.

Author: Alex McGonigle @grannyprogramming
"""

import logging
import json
import os
from datetime import datetime
from modules.config_loader import load_ini_settings, load_config
from modules.trello_api import get_board_id
from modules.board_operations import (
    set_board_background_image,
    manage_board_lists,
    create_missing_labels,
    manage_this_week_list
)
from modules.card_operations import process_all_problem_cards, retest_cards

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_trello_board(config, settings):
    """
    Set up the Trello board for operations.
    
    Ensures the board exists, sets its background image, manages its lists, and creates any missing labels.
    """
    board_id = get_board_id(config, settings, settings["BOARD_NAME"])
    if board_id is None:
        logging.error("Failed to retrieve board ID.")
        return None
    set_board_background_image(board_id)
    manage_board_lists(board_id)
    create_missing_labels(board_id)
    return board_id


def process_cards(config, settings, board_id, topics, current_date):
    """
    Process Trello cards for a given board and date.
    
    Processes all problem cards, populates the "To Do this Week" list, and manages card retests.
    """
    process_all_problem_cards(config, settings, board_id, topics, current_date)
    manage_this_week_list(config, settings, board_id)
    retest_cards(config, settings, settings["BOARD_NAME"], current_date)



def main():
    """
    The main function that coordinates the primary operations.
    
    Loads configurations, sets up the Trello board, and processes the cards.
    """
    config = load_config()
    settings = load_ini_settings()

    # Load topics from the JSON file
    topics_path = os.environ.get("TOPICS_JSON_PATH", "./config/leetcode75.json")
    with open(topics_path, "r", encoding="utf-8") as file:
        topics = json.load(file)

    current_date = datetime.now()

    # Set up the Trello board
    board_id = setup_trello_board(config, settings)
    if not board_id:
        exit(1)

    process_cards(config, settings, board_id, topics, current_date)

    logging.info("Main script execution completed!")

if __name__ == "__main__":
    main()
