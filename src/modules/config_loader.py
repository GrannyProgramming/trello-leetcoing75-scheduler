"""
Configuration Loading Module.

This module provides utility functions to facilitate loading configuration and settings 
for interacting with the Trello API. Configuration and settings can be loaded from both 
INI files and environment variables.

Functions:
    - load_ini_settings: Loads settings from an INI file and returns them as a dictionary.
    - load_config: Loads API and other related configurations from environment variables.

Dependencies:
    - os: Used to access environment variables.
    - configparser: Used to parse INI configuration files.

Usage:
    Ensure that the required settings are available in ".config/settings.ini" for `load_ini_settings` 
    and the required environment variables are set for `load_config` before invoking these functions.

Note:
    - Keep the ".config/settings.ini" file secure as it might contain sensitive settings.
    - Ensure environment variables such as API_KEY, OAUTH_TOKEN, RAW_URL_BASE, and TOPICS_JSON_PATH 
      are set before using the `load_config` function.

Author: Alex McGonigle @grannyprogramming
"""


import os
import configparser


def load_ini_settings():
    config = configparser.ConfigParser()
    config.read("config/settings.ini")

    return {
        "BASE_URL": config["TRELLO"]["BASE_URL"],
        "BOARD_NAME": config["TRELLO"]["BOARD_NAME"],
        "DEFAULT_LISTS": config["LISTS"]["DEFAULTS"].split(", "),
        "REQUIRED_LISTS": config["LISTS"]["REQUIRED"].split(", "),
        "START_DAY": int(config["WEEK"]["START_DAY"]),
        "END_DAY": int(config["WEEK"]["END_DAY"]),
        "WORKDAYS": int(config["WEEK"]["WORKDAYS"]),
        "DEFAULT_LABELS_COLORS": dict(
            item.split(":") for item in config["LABELS"]["DEFAULT_COLORS"].split(", ")
        ),
        "PROBLEMS_PER_DAY": int(config["PROBLEMS"]["PROBLEMS_PER_DAY"]),
    }


def load_config():
    return {
        "API_KEY": os.environ.get("API_KEY"),
        "OAUTH_TOKEN": os.environ.get("OAUTH_TOKEN"),
        "RAW_URL_BASE": os.environ.get("RAW_URL_BASE"),
        "TOPICS_JSON_PATH": os.environ.get("TOPICS_JSON_PATH"),
    }
