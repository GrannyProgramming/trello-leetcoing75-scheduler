"""
Trello API Integration Module.

This module provides utility functions to facilitate interactions with the Trello API.
It supports operations such as fetching board IDs, checking the existence of cards,
creating lists, checking the existence of lists, deleting lists, fetching member IDs,
uploading custom board backgrounds, and setting custom board backgrounds.

Constants:
    TRELLO_ENTITY (dict): Dictionary mapping entity names to their corresponding Trello API endpoints.

Functions:
    - make_request: Sends an HTTP request and returns a parsed JSON response.
    - trello_request: Sends a request specifically to the Trello API.
    - get_board_id: Retrieves the board ID based on the provided board name.
    - card_exists: Checks if a specific card exists on a board.
    - create_list: Creates a new list on a specified board.
    - check_list_exists: Checks if a list exists on a board.
    - delete_list: Deletes a specified list from a board.
    - get_member_id: Retrieves the ID of the member using the Trello API.
    - upload_custom_board_background: Uploads a custom background image for a board.
    - set_custom_board_background: Sets a custom background for a board.

Dependencies:
    - logging: Used for logging information and error messages.
    - os: Used for joining paths.
    - requests: Used to send HTTP requests.

Note:
    Ensure that the required Trello API credentials are available in the `config` dictionary 
    when calling functions from this module.

Author: Alex McGonigle @grannyprogramming

"""

import logging
import os
import requests

# Constants
TRELLO_ENTITY = {"BOARD": "boards", "MEMBER": "members", "LIST": "lists"}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def make_request(url, method, params=None, data=None, timeout=None, files=None):
    """Send a request and handle exceptions and logging."""
    try:
        with requests.request(
            method, url, params=params, data=data, timeout=timeout, files=files
        ) as response:
            response.raise_for_status()
            return response.json()
    except (requests.RequestException, requests.exceptions.JSONDecodeError) as error:
        logging.error("Request to %s failed. Error: %s", url, error)
        return None


def trello_request(
    config,
    settings,
    resource,
    method="GET",
    entity="",
    board_id=None,
    timeout=None,
    files=None,
    **kwargs,
):
    """Make a request to the Trello API."""
    if board_id:
        resource_url = os.path.join(board_id, resource.lstrip("/"))
    else:
        resource_url = resource.lstrip("/")

    url = os.path.join(settings["BASE_URL"], entity, resource_url)

    query = {"key": config["API_KEY"], "token": config["OAUTH_TOKEN"], **kwargs}

    logging.info("Making a request to endpoint: %s with method: %s", method, url)
    return make_request(
        url, method, params=query, data=None, timeout=timeout, files=files
    )


def create_board(config, settings, board_name):
    """Create a new Trello board and return its ID."""
    new_board = trello_request(
        config, settings, resource="/boards", method="POST", name=board_name
    )

    # Log the response for debugging
    logging.info("Response from board creation: %s", new_board)

    if new_board and 'id' in new_board:
        return new_board["id"]
    else:
        logging.error("Failed to create board with name: %s", board_name)
        return None


def get_board_id(config, settings, board_name):
    """Get the board ID given a board name. If the board does not exist, create it."""
    boards = trello_request(config, settings, resource="members/me/boards")

    if boards:
        for board in boards:
            if board["name"] == board_name:
                return board["id"]

    # If board doesn't exist, create it
    return create_board(config, settings, board_name)


def card_exists(config, settings, board_id, card_name):
    """Check if a card exists on the board."""
    cards = trello_request(config, settings, f"{board_id}/cards")
    return any(card["name"] == card_name for card in cards)


def create_list(config, settings, board_id, list_name):
    """Create a new list on a board."""
    return trello_request(
        config,
        settings,
        "",
        method="POST",
        entity=TRELLO_ENTITY["LIST"],
        idBoard=board_id,
        name=list_name,
    )


def check_list_exists(config, settings, board_id, list_name):
    """Check if a list exists on the board."""
    lists = trello_request(config, settings, f"{board_id}/lists")
    return any(lst["name"] == list_name for lst in lists)


def delete_list(config, settings, board_id, list_name):
    """Delete a list on the board."""
    lists = trello_request(config, settings, f"{board_id}/lists")
    list_id = next(lst["id"] for lst in lists if lst["name"] == list_name)
    return trello_request(
        config,
        settings,
        f"{list_id}/closed",
        method="PUT",
        entity=TRELLO_ENTITY["LIST"],
        value="true",
    )


def get_member_id(config, settings):
    """Retrieve the member ID."""
    response = trello_request(config, settings, "me", entity=TRELLO_ENTITY["MEMBER"])
    return response.get("id") if response else None


def upload_custom_board_background(config, settings, member_id, image_filepath):
    """Upload a custom background image for the board."""
    endpoint = f"members/{member_id}/customBoardBackgrounds"
    with open(image_filepath, "rb") as file:
        files = {"file": (os.path.basename(image_filepath), file, "image/png")}
        response = trello_request(
            config, settings, endpoint, method="POST", entity="", files=files
        )
    return response.get("id") if response else None


def set_custom_board_background(config, settings, board_id, background_id):
    """Set a custom background for the board."""
    endpoint = f"{board_id}/prefs/background"
    response = trello_request(
        config,
        settings,
        endpoint,
        method="PUT",
        entity=TRELLO_ENTITY["BOARD"],
        value=background_id,
    )
    return response if response else None
