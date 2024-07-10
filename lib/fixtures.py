"""
Fixtures are articles stored in the codebase so that they can be added to any
new installation. Command.py allows them to be loaded and saved.
"""

import os

from typing import List

from lib.data import Data
from lib.storage import load_dir, save_dir


def fixtures_list() -> List[str]:
    """
    Returns doc_slugs of documents to load or save as fixtures.
    """
    return ["index", "help"]


def fixtures_dir(doc_slug: str) -> str:
    """
    Finds path to the fixtures directory for a document slug.
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(this_dir, "..", "install", "articles", doc_slug)


def load_user_document(data: Data, user_slug: str, doc_slug: str):
    """
    Loads a directory of text files into a stored document.

    Don't generate the new document, just zap any cached HTML.
    """
    src_dir = fixtures_dir(doc_slug)
    src_dict = load_dir(src_dir)
    data.userDocument_set(user_slug, doc_slug, src_dict, {})
    data.userDocumentCache_delete(user_slug, doc_slug)
    print(f"Loaded: {doc_slug} ({len(src_dict)})")


def save_user_document(data: Data, user_slug: str, doc_slug: str):
    """
    Saves a stored document into a directory as text files.
    """
    dst_dir = fixtures_dir(doc_slug)
    dst_dict = data.userDocument_get(user_slug, doc_slug)
    save_dir(dst_dir, dst_dict)
    print(f"Saved: {doc_slug} ({len(dst_dict)})")


def load_fixtures(data):
    """
    Puts fixtures dirs into Redis as admin user documents.
    """
    for doc_slug in fixtures_list():
        load_user_document(data, data.admin_user, doc_slug)


def save_fixtures(data):
    """
    Puts admin user's fixture docs into fixtures dir for later reload.
    """
    for doc_slug in fixtures_list():
        save_user_document(data, data.admin_user, doc_slug)
