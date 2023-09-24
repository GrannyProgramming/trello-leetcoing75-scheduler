"""
Trello Board Management Module.

This module provides utility functions for managing various aspects of Trello boards.
It supports operations such as fetching and setting board background images, managing board lists,
and creating missing labels on boards.

Functions:
    - fetch_image: Downloads the background image from a specified URL.
    - set_board_background_image: Sets a custom background image for a specified Trello board.
    - manage_board_lists: Manages the default and required lists on a Trello board.
    - create_missing_labels: Creates any missing labels on a specified Trello board based on predefined defaults.

Dependencies:
    - logging: Used for logging information and error messages.
    - .utilities: Contains utility functions including the `download_image` function.
    - .trello_api: Houses Trello-specific API functions.
    - .config_loader: Provides functions to load configurations and settings.

Globals:
    - settings: Global variable storing loaded settings from an INI file.
    - config: Global variable storing loaded configurations.

Note:
    This module depends heavily on the configurations provided in the `config` and `settings` 
    global variables. Ensure these are loaded properly before using functions from this module.

Author: Alex McGonigle @grannyprogramming
"""


import logging
from .utilities import download_image, get_max_cards_for_week
from .card_operations import (
    fetch_all_list_ids,
    fetch_cards_from_list,
    filter_cards_by_label,
    apply_changes_to_board
)
from .trello_api import (
    trello_request,
    get_member_id,
    upload_custom_board_background,
    set_custom_board_background,
    delete_list,
    check_list_exists,
    create_list,
)
from .config_loader import load_ini_settings, load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

settings = load_ini_settings()
config = load_config()


def fetch_image():
    """Fetches the background image from a given URL."""
    return download_image(f"{config['RAW_URL_BASE']}imgs/background/groot.png")


def set_board_background_image(board_id):
    """Sets the board background image."""
    member_id = get_member_id(config, settings)
    if not member_id:
        raise ValueError("Failed to retrieve member ID")

    image_filepath = fetch_image()
    if not image_filepath:
        raise ValueError("Failed to download image")

    background_id = upload_custom_board_background(
        config, settings, member_id, image_filepath
    )
    if not background_id:
        raise ValueError("Failed to upload custom board background image")

    if not set_custom_board_background(config, settings, board_id, background_id):
        raise ValueError("Failed to set board background image")


def manage_board_lists(board_id):
    """Manages the default and required lists for a given board."""
    for default_list in settings["DEFAULT_LISTS"]:
        if check_list_exists(config, settings, board_id, default_list):
            delete_list(config, settings, board_id, default_list)

    for required_list in settings["REQUIRED_LISTS"]:
        if not check_list_exists(config, settings, board_id, required_list):
            create_list(config, settings, board_id, required_list)


def create_missing_labels(board_id):
    """Creates missing labels for a given board."""
    labels = trello_request(config, settings, f"{board_id}/labels", entity="boards")
    if labels is None:
        raise ValueError(f"Failed to fetch labels for board with ID: {board_id}")

    label_names = [l.get("name") for l in labels if "name" in l]
    for label, color in settings["DEFAULT_LABELS_COLORS"].items():
        if label not in label_names:
            trello_request(
                config,
                settings,
                "labels",
                "POST",
                entity="boards",
                board_id=board_id,
                name=label,
                color=color,
            )
            logging.info(
                "Created label %s with color %s for board ID: %s",
                label,
                color,
                board_id,
            )


def manage_this_week_list(local_config, local_settings, board_id):
    """
    Ensure the 'To Do this Week' list has the required number of cards based on the settings.
    Cards with specific labels are excluded from this count.
    """
    max_cards = get_max_cards_for_week(local_settings)
    
    # Fetch list IDs and get the ID for "To Do this Week"
    list_ids = fetch_all_list_ids(local_config, local_settings, board_id)
    to_do_this_week_name = settings["REQUIRED_LISTS"][2]  
    to_do_this_week_id = list_ids.get(to_do_this_week_name)

    
    # Fetch and filter cards
    cards = fetch_cards_from_list(local_config, local_settings, to_do_this_week_id)
    filtered_cards = filter_cards_by_label(cards, local_settings)

    # Calculate the number of cards to pull
    cards_to_pull_count = max_cards - len(filtered_cards)

    logging.info("Need to pull %s cards to meet the weekly quota.", cards_to_pull_count)
    
    apply_changes_to_board(local_config, local_settings, list_ids, cards_to_pull_count)

