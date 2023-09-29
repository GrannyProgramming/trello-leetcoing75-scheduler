"""
Trello API  Module.

This module provides utility functions to interact with the Trello API. It encompasses
a variety of functions for sending requests, constructing URLs, downloading images, and more.

Functions:
    - make_request(url, method, params=None, data=None, timeout=None, files=None): Sends a request to a specified URL and handles exceptions and logging.
    - trello_request(_config, _settings, resource, method="GET", entity="boards", timeout=None, files=None, **kwargs): Sends a request to the Trello API using specified _configurations and _settings.
    - construct_url(base_url, entity, resource, **kwargs): Constructs a URL for the Trello API based on provided parameters.
    - download_image(url, filepath="tmp_image.png"): Downloads an image from a given URL and saves it to a specific path.
    - fetch_cards_from_list(_config, _settings, list_id): Fetches all cards from a given Trello list.

Dependencies:
    - logging: Used for logging information and error messages.
    - requests: Used for making HTTP requests.

Author: Alex McGonigle @grannyprogramming
"""

import logging
import requests


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
    _config,
    _settings,
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
    url = construct_url(_settings["BASE_URL"], entity, resource, **kwargs)

    query = {"key": _config["API_KEY"], "token": _config["OAUTH_TOKEN"]}
    query.update(kwargs)  # Always add the kwargs to the query parameters

    logging.info("Making a request to endpoint: %s with method: %s", method, url)
    return make_request(url, method, params=query, timeout=timeout, files=files)


def construct_url(base_url, entity, resource, **kwargs):
    """
    Construct the URL by joining base_url, entity, board_id (if provided), list_id (if provided), and resource.
    Ensure that there are no double slashes.
    """
    # Prepare a list to hold all components of the URL.
    url_components = [base_url.rstrip("/")]  # Ensure base_url doesn't end with a slash

    # Add the entity (boards, lists, cards, etc.)
    url_components.append(entity)

    # If card_id is provided, add it
    if "card_id" in kwargs and kwargs["card_id"]:
        url_components.append(kwargs["card_id"])
    else:
        # If board_id is provided, add it
        if "board_id" in kwargs and kwargs["board_id"]:
            url_components.append(kwargs["board_id"])

        # If list_id is provided, add it
        if "list_id" in kwargs and kwargs["list_id"]:
            url_components.append(kwargs["list_id"])

    # Add the resource without any leading slash
    url_components.append(resource.lstrip("/"))

    # Debug logs to identify the issue
    logging.debug("URL Components before cleaning: %s", url_components)

    # Filter out None or empty components and join them with '/'
    cleaned_url = "/".join(filter(None, url_components))

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


def fetch_cards_from_list(_config, _settings, list_id):
    """Fetch all cards from a given list."""
    logging.debug("Fetching cards for list_id: %s", list_id)
    if not list_id:
        logging.error("list_id is not provided when trying to fetch cards from a list.")
        return None
    return trello_request(_config, _settings, "cards", entity="lists", list_id=list_id)
