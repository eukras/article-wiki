"""
Fixtures are articles stored in the codebase so that they can be added to any
new installation. See command.py.
"""

import os
from slugify import slugify

from PIL.Image import Image

from lib.data import Data
from lib.storage import read_document_dir, write_document_dir


FIXTURES_LIST = ["index", "help"]

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def fixtures_dir(doc_slug: str) -> str:
    """
    Finds path to the fixtures directory for a document slug.
    """
    return os.path.join(THIS_DIR, "..", "install", "articles", doc_slug)


def load_document(data: Data, user_slug: str, doc_slug: str):
    """
    Loads a directory of text files into a stored document.

    Don't generate the new document, just zap any cached HTML.
    """
    src_dir = fixtures_dir(doc_slug)
    files = read_document_dir(src_dir)
    if text_files := {
        slugify(name.replace(".txt", "")): file
        for name, file in files.items()
        if isinstance(file, str)
    }:
        data.userDocument_set(user_slug, doc_slug, text_files)
    if image_files := {
        name: file
        for name, file in files.items()
        if name.endswith(".png") and isinstance(file, Image)
    }:
        for name, file in image_files.items():
            print(f"  - Reading {user_slug}/{doc_slug}/{name}")
            data.userDocumentImage_set(user_slug, doc_slug, name, file)

    data.userDocumentCache_delete(user_slug, doc_slug)


def save_document(data: Data, user_slug: str, doc_slug: str):
    """
    Saves a stored document into a directory as text files.
    """
    dst_dir = fixtures_dir(doc_slug)
    text_files = data.userDocument_get(user_slug, doc_slug) or {}
    image_files = data.userDocumentImage_hash(user_slug, doc_slug) or {}
    dst_dict = text_files | image_files
    write_document_dir(dst_dir, dst_dict)


def load_fixtures(data):
    """
    Puts fixtures dirs into Redis as admin user documents.
    """
    for doc_slug in FIXTURES_LIST:
        print(f"Loading {data.admin_user}/{doc_slug}")
        load_document(data, data.admin_user, doc_slug)


def save_fixtures(data):
    """
    Puts admin user's fixture docs into fixtures dir for later reload.
    """
    for doc_slug in FIXTURES_LIST:
        print(f"Saving {data.admin_user}/{doc_slug}")
        save_document(data, data.admin_user, doc_slug)
