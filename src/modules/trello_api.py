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
from .utilities import construct_url
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
    entity="boards",  # Default to boards if not specified
    timeout=None,
    files=None,
    **kwargs,
):
    """Send a request to Trello API and return the response."""
    # Filter out None values from kwargs
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    # Construct the URL based on the provided parameters
    url = construct_url(settings['BASE_URL'], entity, resource, **kwargs)

    query = {"key": config["API_KEY"], "token": config["OAUTH_TOKEN"]}
    query.update(kwargs)  # Always add the kwargs to the query parameters

    logging.info("Making a request to endpoint: %s with method: %s", method, url)
    return make_request(
        url, method, params=query, timeout=timeout, files=files
    )




def create_board(config, settings, board_name):
    """Create a new Trello board and return its ID."""
    new_board = trello_request(
        config, settings, resource="", method="POST", name=board_name
    )

    # Log the response for debugging
    logging.info("Response from board creation: %s", new_board)

    if new_board and 'id' in new_board:
        logging.info("Successfully created board with ID: %s", new_board["id"])
        return new_board["id"]
    else:
        logging.error("Failed to create board with name: %s", board_name)
        return None



def get_board_id(config, settings, board_name):
    """Get the board ID given a board name. If the board does not exist, create it."""
    boards = trello_request(config, settings, resource="me/boards", entity="members")
    # Check if board with the given name exists
    board_id = next((board["id"] for board in boards if board["name"] == board_name), None)
    # If board doesn't exist, create it
    if not board_id:
        board_id = create_board(config, settings, board_name)
    if board_id:
        logging.info("Created a new board with ID: %s", board_id)
    else:
        logging.error("Board creation failed.")
    
    return board_id

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


def fetch_cards_from_list(config, settings, list_id):
    """Fetch all cards from a given list."""
    logging.debug("Fetching cards for list_id: %s", list_id)
    if not list_id:
        logging.error("list_id is not provided when trying to fetch cards from a list.")
        return None
    return trello_request(config, settings, "cards", entity="lists", list_id=list_id)

