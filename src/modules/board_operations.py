"""
Trello Board Management Module.

This module provides utility functions for managing various aspects of Trello boards.
It supports operations such as fetching and setting board background images, managing board lists,
creating and deleting labels on boards, creating boards based on names, and more.

Functions:
    - fetch_image(): Downloads the background image from a specified URL.
    - set_board_background_image(board_id): Sets a custom background image for a specified Trello board.
    - manage_board_lists(board_id): Manages the default and required lists on a Trello board.
    - create_missing_labels(board_id): Creates any missing labels on a specified Trello board based on predefined defaults.
    - fetch_all_list_ids(_config, _settings, board_id): Retrieves all list IDs for a given board.
    - fetch_all_label_ids(_config, _settings, board_id): Retrieves all label IDs for a given board.
    - create_board(_config, _settings, board_name): Creates a new Trello board, deletes default lists and labels, and returns its ID.
    - get_board_id(_config, _settings, board_name): Gets the board ID given a board name or creates it if it doesn't exist.
    - delete_list(_config, _settings, board_id, list_name): Deletes a list on a board.
    - check_list_exists(_config, _settings, board_id, list_name): Checks if a list exists on a board.
    - create_list(_config, _settings, board_id, list_name): Creates a new list on a board.
    - upload_custom_board_background(_config, _settings, member_id, image_filepath): Uploads a custom background image for the board.
    - set_custom_board_background(_config, _settings, board_id, background_id): Sets a custom background for the board.
    - get_member_id(_config, _settings): Retrieves the member ID.
    - get_labels_on_board(_config, _settings, board_id): Fetches all labels on a board.
    - delete_label(_config, _settings, label_id): Deletes a specific label.
    - delete_all_labels(_config, _settings, board_id): Deletes all labels on a board.

Dependencies:
    - os: Provides a way of using operating system-dependent functionality.
    - logging: Used for logging information and error messages.
    - .trello_api: Houses Trello-specific API functions.
    - ._config_loader: Provides functions to load configurations and settings.

Globals:
    - _settings: Global variable storing loaded settings from an INI file.
    - _config: Global variable storing loaded configurations.
    - TRELLO_ENTITY: Dictionary containing constants for different Trello entities.

Author: Alex McGonigle @grannyprogramming
"""

import os
import logging
from .trello_api import download_image, trello_request
from .config_loader import load_ini_settings, load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

_settings = load_ini_settings()
_config = load_config()

# Constants
TRELLO_ENTITY = {"BOARD": "boards", "MEMBER": "members", "LIST": "lists"}


def fetch_image():
    """Fetches the background image from a given URL."""
    return download_image(f"{_config['RAW_URL_BASE']}imgs/background/groot.png")


def set_board_background_image(board_id):
    """Sets the board background image."""
    member_id = get_member_id(_config, _settings)
    if not member_id:
        raise ValueError("Failed to retrieve member ID")

    image_filepath = fetch_image()
    if not image_filepath:
        raise ValueError("Failed to download image")

    background_id = upload_custom_board_background(
        _config, _settings, member_id, image_filepath
    )
    if not background_id:
        raise ValueError("Failed to upload custom board background image")

    if not set_custom_board_background(_config, _settings, board_id, background_id):
        raise ValueError("Failed to set board background image")


def manage_board_lists(board_id):
    """Manages the required lists for a given board."""

    for required_list in _settings["REQUIRED_LISTS"]:
        if not check_list_exists(_config, _settings, board_id, required_list):
            create_list(_config, _settings, board_id, required_list)


def create_missing_labels(board_id):
    """Creates missing labels for a given board."""
    labels = trello_request(_config, _settings, f"{board_id}/labels", entity="boards")
    if labels is None:
        raise ValueError(f"Failed to fetch labels for board with ID: {board_id}")

    label_names = [l.get("name") for l in labels if "name" in l]
    for label, color in _settings["DEFAULT_LABELS_COLORS"].items():
        if label not in label_names:
            trello_request(
                _config,
                _settings,
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


def fetch_all_list_ids(_config, _settings, board_id):
    """Retrieve all list IDs for a given board."""
    response = trello_request(_config, _settings, f"{board_id}/lists")
    if response is None:
        logging.error("Failed to fetch lists for board with ID: %s", board_id)
        return {}
    list_ids = {l["name"]: l["id"] for l in response}
    logging.debug("Fetched list IDs: %s", list_ids)
    return list_ids


def fetch_all_label_ids(_config, _settings, board_id):
    """Retrieve all label IDs for a given board."""
    response = trello_request(
        _config, _settings, "labels", entity="boards", board_id=board_id
    )
    if response is None:
        logging.error("Failed to fetch labels for board with ID: %s", board_id)
        return {}
    return {l["name"]: l["id"] for l in response}


def create_board(_config, _settings, board_name):
    """Create a new Trello board, delete default lists, delete all labels, and return its ID."""
    new_board = trello_request(
        _config, _settings, resource="", method="POST", name=board_name
    )

    # Log the response for debugging
    logging.info("Response from board creation: %s", new_board)

    if new_board and "id" in new_board:
        logging.info("Successfully created board with ID: %s", new_board["id"])

        # Delete default lists for the newly created board
        for default_list in _settings["DEFAULT_LISTS"]:
            if check_list_exists(_config, _settings, new_board["id"], default_list):
                delete_list(_config, _settings, new_board["id"], default_list)

        # Delete all labels for the newly created board
        delete_all_labels(_config, _settings, new_board["id"])

        return new_board["id"]
    else:
        logging.error("Failed to create board with name: %s", board_name)
        return None


def get_board_id(_config, _settings, board_name):
    """Get the board ID given a board name. If the board does not exist or is closed, create it."""
    boards = trello_request(_config, _settings, resource="me/boards", entity="members")

    # Check if an open board with the given name exists
    board_id = next(
        (
            board["id"]
            for board in boards
            if board["name"] == board_name and not board["closed"]
        ),
        None,
    )

    # If board doesn't exist or is closed, create it
    if not board_id:
        board_id = create_board(_config, _settings, board_name)
        logging.info("Created a new board with ID: %s", board_id)
    else:
        logging.info("Using existing board with ID: %s", board_id)

    if not board_id:
        logging.error("Failed to find or create a board with name: %s", board_name)

    return board_id


def delete_list(_config, _settings, board_id, list_name):
    """Delete a list on the board."""
    lists = trello_request(_config, _settings, f"{board_id}/lists")
    list_id = next(lst["id"] for lst in lists if lst["name"] == list_name)
    return trello_request(
        _config,
        _settings,
        f"{list_id}/closed",
        method="PUT",
        entity=TRELLO_ENTITY["LIST"],
        value="true",
    )


def check_list_exists(_config, _settings, board_id, list_name):
    """Check if a list exists on the board."""
    lists = trello_request(_config, _settings, f"{board_id}/lists")
    return any(lst["name"] == list_name for lst in lists)


def create_list(_config, _settings, board_id, list_name):
    """Create a new list on a board."""
    return trello_request(
        _config,
        _settings,
        "",
        method="POST",
        entity=TRELLO_ENTITY["LIST"],
        idBoard=board_id,
        name=list_name,
    )


def upload_custom_board_background(_config, _settings, member_id, image_filepath):
    """Upload a custom background image for the board."""
    endpoint = f"members/{member_id}/customBoardBackgrounds"
    with open(image_filepath, "rb") as file:
        files = {"file": (os.path.basename(image_filepath), file, "image/png")}
        response = trello_request(
            _config, _settings, endpoint, method="POST", entity="", files=files
        )
    return response.get("id") if response else None


def set_custom_board_background(_config, _settings, board_id, background_id):
    """Set a custom background for the board."""
    endpoint = f"{board_id}/prefs/background"
    response = trello_request(
        _config,
        _settings,
        endpoint,
        method="PUT",
        entity=TRELLO_ENTITY["BOARD"],
        value=background_id,
    )
    return response if response else None


def get_member_id(_config, _settings):
    """Retrieve the member ID."""
    response = trello_request(_config, _settings, "me", entity=TRELLO_ENTITY["MEMBER"])
    return response.get("id") if response else None


def get_labels_on_board(_config, _settings, board_id):
    """Fetch all labels on the board."""
    return trello_request(_config, _settings, f"{board_id}/labels")


def delete_label(_config, _settings, label_id):
    """Delete a label."""
    return trello_request(
        _config, _settings, label_id, method="DELETE", entity="labels"
    )


def delete_all_labels(_config, _settings, board_id):
    """Delete all labels on the board."""
    labels = get_labels_on_board(_config, _settings, board_id)
    for label in labels:
        delete_label(_config, _settings, label["id"])
