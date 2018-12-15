#!/usr/bin/python
# vim: set fileencoding: UTF8 :

"""
Command Line tool for Wiki admin.

save_user_document: Copy from Redis to install folders.
load_user_document: Copy from install folders to Redis.
"""

import os
import sys

import click

from typing import List

from lib.data import Data, load_env_config
from lib.document import Document
from lib.storage import load_dir, save_dir


# ------------------------
# Utility functions.
# ------------------------


def fixtures_list() -> List[str]:
    """Returns slugs of documents to load or save as fixtures."""
    return ['fixtures', 'help']


def fixtures_dir(doc_slug: str) -> str:
    """Finds path to the fixtures directory for a document slug."""
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ROOT_DIR, 'install', doc_slug)


def get_redis_client() -> Data:
    """Initialises a Redis client from environment variables."""
    config = load_env_config()
    if "pytest" in sys.modules:
        config['REDIS_DATABASE'] = '1'
    return Data(config)


def load_user_document(data: Data, user_slug: str, doc_slug: str):
    """
    Loads a directory of text files into a stored document.

    Don't generate the new document, just zap any cached HTML.
    """
    src_dir = fixtures_dir(doc_slug)
    src_dict = load_dir(src_dir)
    data.userDocument_set(user_slug, doc_slug, src_dict, {})
    data.userDocumentCache_delete(user_slug, doc_slug)
    print("Loaded: {} ({:d})".format(doc_slug, len(src_dict)))


def save_user_document(data: Data, user_slug: str, doc_slug: str):
    """Saves a stored document into a directory as text files."""
    dst_dir = fixtures_dir(doc_slug)
    dst_dict = data.userDocument_get(user_slug, doc_slug)
    save_dir(dst_dir, dst_dict)
    print("Saved: {} ({:d} files)".format(doc_slug, len(dst_dict)))


# ------------------------
# Commands
# ------------------------


def create_admin_user():
    """
    Creates an $ADMIN_USER with $ADMIN_USER_PASSWORD.
    """
    config = load_env_config()
    data = get_redis_client()
    data.user_set(config['ADMIN_USER'], config['ADMIN_USER_PASSWORD'])
    print("Created user: {:s}".format(config['ADMIN_USER']))


def load_fixtures():
    """Puts fixtures dirs into Redis as admin user fixture documents."""
    data = get_redis_client()
    for doc_slug in fixtures_list():
        load_user_document(data, data.admin_user, doc_slug)


def save_fixtures():
    """Puts admin user's fixture docs into fixtures dir for later reload."""
    data = get_redis_client()
    for doc_slug in fixtures_list():
        save_user_document(data, data.admin_user, doc_slug)


def refresh_metadata():
    """Cycle through all documents for all users and regenerate their cache and
    metadata entries."""
    data = get_redis_client()
    for user_slug in data.userSet_list():
        for doc_slug in data.userDocumentSet_list(user_slug):
            document = Document(data)
            document.load(user_slug, doc_slug)
            document.save()


# ------------------------
# Handle query.
# ------------------------


@click.command()
@click.argument('command')
def console(command):
    """Processes console commands."""
    if command == 'initialize':
        create_admin_user()
        load_fixtures()
    elif command == 'load-fixtures':
        load_fixtures()
    elif command == 'refresh-metadata':
        refresh_metadata()
    elif command == 'save-fixtures':
        save_fixtures()
    else:
        print("Commands:")
        print("  - initialize")
        print("  - load-fixtures")
        print("  - refresh_metadata")
        print("  - save-fixtures")


if __name__ == '__main__':
    console()
