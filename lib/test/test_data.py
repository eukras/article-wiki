"""
Test the redis interface for user and docs handling.
"""

import pytest
from .context import lib  # noqa: F401

from lib.data import Data
from lib.wiki.sample_data import minimal_document
from lib.wiki.utils import random_slug


# Disable this for no; TODO: Tag as integrations.
pytest.skip(allow_module_level=True)


config = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'REDIS_DATABASE': 1,  # <-- TESTING
    'ADMIN_USER': 'admin',
    'TIME_ZONE': 'Australia/Sydney',
}
data = Data(config, strict=True)
data.redis.flushdb()


def test_utility_functions():
    """
    Create a hash, find its key, delete it.
    """
    prefix = 'test-utilities-'
    test_slug = random_slug(prefix)
    data.redis.hmset(test_slug, minimal_document)
    assert data.redis.exists(test_slug)
    assert data.get_hashes([test_slug]) == [minimal_document]
    assert data.keys_by_prefix(prefix) == [test_slug]
    data.del_keys([test_slug])
    assert not data.redis.exists(test_slug)


def test_auth_functions():
    """
    Create a token, get it, delete it.
    """
    test_user = {'slug': 'test'}
    token = data.login_set(test_user)
    assert data.login_get('wrong-token') is None
    assert data.login_get(token) == test_user
    data.login_delete(token)
    assert data.login_get(token) is None


def test_check_slugs():
    """
    Confirm that bad slugs cause ValueErrors
    """
    good_slugs = ['ok-good', '123-890']
    bad_slugs = ['no_terrible', '!@#$%^&*(']
    try:
        data.check_slugs(*good_slugs)
        assert True
    except ValueError:
        assert False
    try:
        data.check_slugs(*bad_slugs)
        assert False
    except ValueError:
        assert True


def test_userSet():
    """
    User Set -- A set of user_slugs: Can be used to construct keys
    for user dicts and other objects. Add a user to the user set;
    delete.

    v.0.1.0 -- SINGLE_USER, so no pagination yet.
    """
    test_slug = random_slug('test-user-')
    count = data.userSet_count()

    data.userSet_set(test_slug)
    data.userSet_set(test_slug)  # <-- no effect
    assert data.userSet_exists(test_slug)
    assert test_slug in data.userSet_list()
    assert count + 1 == data.userSet_count()

    data.userSet_delete(test_slug)
    assert not data.userSet_exists(test_slug)
    assert test_slug not in data.userSet_list()
    assert count == data.userSet_count()


def test_users():
    """
    Users -- Redis Hashes of user names and whether they're
    admins.

    v.0.1.0 -- SINGLE_USER, so not super-important yet.
    """
    user_slug = random_slug('test-user-')
    key = data.user_key(user_slug)
    assert user_slug in key

    test_user = {'slug': 'my-name', 'is_admin': 'NO', 'password': 'password'}
    assert not data.user_exists(user_slug)
    data.user_set(user_slug, test_user)
    assert data.user_exists(user_slug)
    assert data.user_get(user_slug) == test_user
    assert data.user_get('nonexistent-user') is None
    assert data.user_hash()[user_slug] == test_user

    data.user_delete(user_slug)
    assert not data.user_exists(user_slug)
    assert data.user_get(user_slug) is None


def test_userDocumentSet():
    """
    UserDocumentSet -- a set of doc_slugs for each user.

    v.0.1.0 -- SINGLE_USER, so no pagination yet.
    """
    user_slug = random_slug('test-user-')
    key = data.userDocumentSet_key(user_slug)
    assert user_slug in key

    doc_slug = random_slug('test-document-')
    assert not data.userDocumentSet_exists(user_slug, doc_slug)

    data.userDocumentSet_set(user_slug, doc_slug)
    assert data.userDocumentSet_exists(user_slug, doc_slug)
    assert data.userDocumentSet_count(user_slug) == 1
    assert data.userDocumentSet_list(user_slug) == [doc_slug]

    data.userDocumentSet_delete(user_slug, doc_slug)
    assert not data.userDocumentSet_exists(user_slug, doc_slug)
    assert data.userDocumentSet_count(user_slug) == 0
    assert data.userDocumentSet_list(user_slug) == []


def test_userDocuments():
    """
    UserDocuments -- Redis Hashes of {part_slug: wiki_text}.

    Generally speaking, userDocument_ methods manage userSet data.
    """
    user_slug = random_slug('test-user-')
    doc_slug = random_slug('test-document-')
    key = data.userDocument_key(user_slug, doc_slug)
    assert user_slug in key
    assert doc_slug in key

    assert not data.userDocument_exists(user_slug, doc_slug)

    data.userDocument_set(user_slug, doc_slug, minimal_document)
    assert data.userDocument_exists(user_slug, doc_slug)
    assert data.userDocument_get(user_slug, doc_slug) == minimal_document
    assert data.userDocument_hash(user_slug) == {doc_slug: minimal_document}

    new_slug = data.userDocument_unique_slug(user_slug, doc_slug)
    assert new_slug != doc_slug

    data.userDocument_delete(user_slug, doc_slug)
    assert not data.userDocument_exists(user_slug, doc_slug)
    assert data.userDocument_get(user_slug, doc_slug) is None

    # get_list ?
    # get_dict / archive ?


def test_userDocumentMetadata():
    """
    UserDocumentMetadata -- Redis Hashes of {key: val}.

    Generally speaking, userDocument_ methods manage userSet data.
    """
    user_slug = random_slug('test-user-')
    doc_slug = random_slug('test-document-')
    key = data.userDocumentMetadata_key(user_slug, doc_slug)
    assert user_slug in key
    assert doc_slug in key

    assert not data.userDocumentMetadata_exists(user_slug, doc_slug)

    metadata = {'doc_slug': doc_slug, 'word_count': '3000'}  # <-- str for num
    data.userDocumentMetadata_set(user_slug, doc_slug, metadata)
    assert data.userDocumentMetadata_get(user_slug, doc_slug) == metadata
    assert data.userDocumentMetadata_exists(user_slug, doc_slug)

    data.userDocumentMetadata_delete(user_slug, doc_slug)
    assert data.userDocumentMetadata_get(user_slug, doc_slug) is None
    assert not data.userDocumentMetadata_exists(user_slug, doc_slug)


def test_userDocumentLastChanged():
    """
    Note that last_changed is just a list of metadata keys; so must also create
    metadata....
    """
    user_slug = random_slug('test-user-')
    key = data.userDocumentLastChanged_key(user_slug)
    assert user_slug in key

    assert data.userDocumentLastChanged_list(user_slug) == []

    doc_slug = random_slug('test-document-')
    metadata = {'doc_slug': doc_slug, 'word_count': '3000'}  # <-- str for num
    data.userDocumentLastChanged_set(user_slug, doc_slug, doc_slug)
    data.userDocumentMetadata_set(user_slug, doc_slug, metadata)
    assert data.userDocumentLastChanged_list(user_slug) == [metadata]

    # Check no duplication
    data.userDocumentLastChanged_set(user_slug, doc_slug, doc_slug)
    assert data.userDocumentLastChanged_list(user_slug) == [metadata]

    data.userDocumentLastChanged_delete(user_slug, doc_slug)
    assert data.userDocumentLastChanged_list(user_slug) == []

    # Clean up:
    data.userDocumentMetadata_delete(user_slug, doc_slug)
    assert not data.userDocumentMetadata_exists(user_slug, doc_slug)


def test_userDocumentCache():
    user_slug = random_slug('test-user-')
    doc_slug = random_slug('test-document-')
    key = data.userDocumentCache_key(user_slug, doc_slug)
    assert user_slug in key
    assert doc_slug in key

    assert not data.userDocumentCache_exists(user_slug, doc_slug)

    html = "<article>...</article>"
    data.userDocumentCache_set(user_slug, doc_slug, html)
    assert data.userDocumentCache_exists(user_slug, doc_slug)
    assert data.userDocumentCache_get(user_slug, doc_slug) == html

    data.userDocumentCache_delete(user_slug, doc_slug)
    assert not data.userDocumentCache_exists(user_slug, doc_slug)
    assert data.userDocumentCache_get(user_slug, doc_slug) is None
