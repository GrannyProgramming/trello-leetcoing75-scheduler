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
    populate_this_week_list,
)
from modules.card_operations import process_all_problem_cards, retest_cards

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    config = load_config()
    settings = load_ini_settings()

    # Load topics from the JSON file
    topics_path = os.environ.get("TOPICS_JSON_PATH", "./config/leetcode75.json")
    with open(topics_path, "r", encoding="utf-8") as file:
        topics = json.load(file)

    current_date = datetime.now()

    # Set up the Trello board
    board_id = get_board_id(config, settings, settings["BOARD_NAME"])
    if board_id is None:
        logging.error("Failed to retrieve board ID. Exiting...")
        exit(1)

    set_board_background_image(board_id)
    manage_board_lists(board_id)
    create_missing_labels(board_id)

    process_all_problem_cards(
        config, settings, board_id, topics, current_date
    )
    
    # Process all problem cards for a given board
    process_all_problem_cards(config, settings, board_id, topics, current_date)
    populate_this_week_list(board_id)
    # Process cards for retesting
    retest_cards(config, settings, settings["BOARD_NAME"], current_date)

    logging.info("Main script execution completed!")
