"""
Document-wide functions.

Tests:
    lib/document.py
"""

from .context import lib  # noqa: F401

from lib.data import Data
from lib.document import Document
from lib.wiki.sample_data import minimal_document
from lib.wiki.utils import random_slug, trim

config = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'REDIS_DATABASE': 1,  # <-- TESTING
    'ADMIN_USER': 'admin',
    'TIME_ZONE': 'Australia/Sydney',
}

data = Data(config, strict=True)


# Basic, untested
# def __init__(self, data: Data = None):
# def __repr__(self):
# def protected_part_slugs(self):

# Basic load/save/delete.
# def load(self, user_slug: str, doc_slug: str) -> bool:
# def save(self, pregenerate=True, update_doc_slug=True):
# def delete(self):

def test_repr_save_load_delete():
    """
    Confirms data in data out. Builds upon data.py.
    """
    data.redis.flushdb()

    user_slug = random_slug('test-user-')
    doc_slug = random_slug('test-doc-')
    doc = Document(data)
    doc.set_parts(user_slug, doc_slug, minimal_document)

    # Create
    new_doc_slug = doc.save(pregenerate=True, update_doc_slug=True)

    assert user_slug in str(doc)
    assert new_doc_slug in str(doc)
    assert "(3 parts)" in str(doc)

    assert new_doc_slug == 'example-document'
    assert data.userSet_exists(user_slug)
    assert data.userDocument_exists(user_slug, new_doc_slug)

    latest_slugs = [
        _['slug'] for _ in data.userDocumentLastChanged_list(user_slug)
    ]
    assert new_doc_slug in latest_slugs
    assert data.userDocumentMetadata_exists(user_slug, new_doc_slug)
    assert data.userDocumentCache_exists(user_slug, new_doc_slug)
    assert data.userDocumentSet_exists(user_slug, new_doc_slug)

    # Rename
    doc.set_index(trim("""
        New Example Document

        Text Goes Here!
    """))
    new_doc_slug = doc.save(pregenerate=True, update_doc_slug=True)
    assert new_doc_slug == "new-example-document"

    assert not data.userDocumentSet_exists(user_slug, doc_slug)
    assert not data.userDocument_exists(user_slug, doc_slug)
    assert not data.userDocumentMetadata_exists(user_slug, doc_slug)
    assert not data.userDocumentCache_exists(user_slug, doc_slug)

    latest_metadata = data.userDocumentLastChanged_list(user_slug)
    assert not any([_.get('slug') == doc_slug for _ in latest_metadata])
    assert any([_.get('slug') == new_doc_slug for _ in latest_metadata])

    assert data.userDocumentSet_exists(user_slug, new_doc_slug)
    assert data.userDocument_exists(user_slug, new_doc_slug)
    assert data.userDocumentMetadata_exists(user_slug, new_doc_slug)
    assert data.userDocumentCache_exists(user_slug, new_doc_slug)
    assert data.userDocumentSet_exists(user_slug, new_doc_slug)

    doc2 = Document(data)
    doc2.load(user_slug, new_doc_slug)

    assert doc.user_slug == doc2.user_slug
    assert doc.doc_slug == doc2.doc_slug
    assert doc.parts == doc2.parts

    # Delete
    doc.delete()

    assert not data.userDocument_exists(user_slug, new_doc_slug)
    assert not data.userDocumentSet_exists(user_slug, new_doc_slug)
    assert not data.userDocumentMetadata_exists(user_slug, new_doc_slug)
    latest_metadata = data.userDocumentLastChanged_list(user_slug)
    assert not any([_.get('slug') == new_doc_slug for _ in latest_metadata])
    assert not data.userDocumentCache_exists(user_slug, new_doc_slug)



# Testing automatic updates for the Table of Contents:
# def set_index(self, new_text: str) -> Union[str, None]:
# def set_part(self, old_slug: str, new_text: str) -> Union[str, None]:
# def delete_part(self, part_slug: str):


def test_set_part():
    """Confirms that the index is updated when a part is renamed."""
    test_parts = {
        'index': trim("""
            Index

            ` Part One
            ` Part Two
            """),
        'part-one': trim("""
            Part One

            Text.
            """),
        'part-two': trim("""
            Part Two

            Text.
            """)
    }
    doc = Document(data)
    doc.set_parts('user-slug', 'doc-slug', test_parts)
    old_slug = 'part-one'
    new_text = trim("""
        Part Three

        Text.
        """)
    new_part_slug = doc.set_part(old_slug, new_text)
    assert new_part_slug == "part-three"
    assert doc.parts == {
        'index': trim("""
            Index

            ` Part Three
            ` Part Two
            """),
        'part-three': trim("""
            Part Three

            Text.
            """),
        'part-two': trim("""
            Part Two

            Text.
            """)
    }


def test_delete_part():
    """Confirms that the index is updated when a part is deleted."""
    test_parts = {
        'index': trim("""
            Index

            ` Part One
            ` Part Two
            """),
        'part-one': trim("""
            Part One

            Text.
            """),
        'part-two': trim("""
            Part Two

            Text.
            """)
    }
    doc = Document(data)
    doc.set_parts('user-slug', 'doc-slug', test_parts)
    doc.delete_part('part-one')
    assert doc.parts == {
        'index': trim("""
            Index

            ` Part Two
            """),
        'part-two': trim("""
            Part Two

            Text.
            """)
    }


# def export_txt_file(self) -> (str, str):
#     def make_txt_name(user_slug: str, doc_slug: str) -> str:
#     def make_txt_divider(number: str, part_slug: str) -> str:
# def import_txt_file(self, user_slug: str, doc_slug: str, file_text: str):

def test_import_and_export_document():
    """
    Generates an archive file and then turns it back into the original parts.
    """
    doc1 = Document(data)
    user_slug = random_slug('test-user-')
    doc_slug = random_slug('test-doc-')
    doc1.set_parts(user_slug, doc_slug, minimal_document)
    file_name, file_text = doc1.export_txt_file()
    assert user_slug in file_name
    assert doc_slug in file_name
    doc2 = Document(data)
    doc2.import_txt_file(user_slug, doc_slug, file_text)
    assert doc1 == doc2
