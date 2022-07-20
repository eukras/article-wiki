# -------------
# TEST STRATEGY
# -------------
# Connect to DB #1 (not #0, which is for the app.)
# Run intialisation command to create the basic system and index its metadata.
# Perform application tests for SINGLE_USER mode of v.0.1.0
# - Basic nav, with login and logout
# - CRUD for docs and parts, while testing indexing consistency.
# FlushDB #1 and exit.


import logging
import pytest
import sys

# Disable this for no; TODO: Tag as integrations.
pytest.skip(allow_module_level=True)

from webtest import TestApp as AppTester  # so not collected?

from context import app, lib  # noqa: F401: F401

from command import load_fixtures
from lib.data import Data, load_env_config
from lib.wiki.utils import trim


# ----------------
# INITIALISATION
# ----------------

config = load_env_config()
if "pytest" in sys.modules:
    logging.info("Running in PyTest: Reconfiguring to use test database.")
    config['REDIS_DATABASE'] = config['REDIS_TEST_DATABASE']

data = Data(config)  # <-- DB 1 for tests

test = AppTester(app.bottleApp)

if config['SINGLE_USER'] != 'YES':
    raise NotImplementedError("v. 0.1.0 does not implement multi-user mode.")


# -------------
# COMMON DATA
# -------------

ADMIN_USER = config['ADMIN_USER']  # <-- v.0.1.0, SINGLE_USER mode

USER_URI = '/user/{:s}'
EDIT_URI = '/edit/{:s}/{:s}/{:s}'
READ_URI = '/read/{:s}/{:s}'

HOME_URI = '/'
EDITOR_URI = '/playground'
HELP_URI = '/help'
LOGIN_URI = '/login'
LOGOUT_URI = '/logout'

ADMIN_HOME_URI = USER_URI.format(ADMIN_USER)
ADMIN_HELP_URI = READ_URI.format(ADMIN_USER, 'help')

HTTP_OK = 200
HTTP_REDIRECT = 302
HTTP_NOT_FOUND = 404


# ------------
# 0. UTILITIES
# ------------

def reset_database():
    data.redis.flushdb()
    data.login_create(config['ADMIN_USER'], config['ADMIN_USER_PASSWORD'])
    load_fixtures()

def do_logout():
    test.get(LOGOUT_URI)


def do_login_as_admin():
    login_page = test.get(LOGIN_URI)
    form = login_page.form
    form['username'] = config['ADMIN_USER']
    form['password'] = config['ADMIN_USER_PASSWORD']
    _ = form.submit()
    assert _.status_int == HTTP_REDIRECT  # Redirect
    assert _.headers['location'].endswith(HOME_URI)


def match_link(uri):
    """
    XPath to match an a.href attribute
    """
    return "//a[@href='{:s}']".format(uri)


# ---------------------------
# 1. NAVIGATION WITHOUT LOGIN
# ---------------------------

@pytest.mark.integration
def test_nothing():
    """
    Pytest executes test functions in order. Resetting the DB at the start of
    this test file allows `pytest` to run the WebTests with a clean dataset.
    """
    reset_database();
    assert True


@pytest.mark.integration
def test_homepage():
    """Main landing page."""
    do_logout()
    _ = test.get(HOME_URI, status=HTTP_REDIRECT)
    if config['SINGLE_USER'] == 'YES':
        assert _.headers['location'].endswith(ADMIN_HOME_URI)
    else:
        assert _.headers['location'].endswith('/')


@pytest.mark.integration
def test_admin_user_page():
    """List admin user's articles, incl. link to help."""
    do_logout()
    _ = test.get(ADMIN_HOME_URI, status=HTTP_OK)
    nav_links = [
        ADMIN_HELP_URI,
        EDITOR_URI,
        LOGIN_URI,
    ]
    for href in nav_links:
        assert _.lxml.xpath(match_link(href))


@pytest.mark.integration
def test_editor_page():
    """Editor page has buttons, textarea and main"""
    do_logout()
    _ = test.get(EDITOR_URI, status=HTTP_OK)
    assert _.lxml.xpath("//textarea")
    assert _.lxml.xpath("//main")


@pytest.mark.integration
def test_help_page():
    # Help page (with standard lengthy content)
    do_logout()
    _ = test.get(HELP_URI, status=HTTP_REDIRECT)
    assert _.headers['location'].endswith(ADMIN_HELP_URI)
    _ = _.follow(status=HTTP_OK)  # <-- New response
    assert _.lxml.xpath("count(//section)") > 30


@pytest.mark.integration
def test_bad_login_fails():
    login_page = test.get(LOGIN_URI)
    form = login_page.form
    form['username'] = "Bad Username"
    form['password'] = "Wrong Password"
    _ = form.submit(status=HTTP_REDIRECT)
    assert _.headers['location'].endswith(LOGIN_URI)

    # TODO: Solve issue with flash messaging in this test.
    # __ = _.follow()
    # assert __.status_int == HTTP_OK
    # assert "Login failed" in __


# ------------------------
# 2. NAVIGATION WITH LOGIN
# ------------------------


@pytest.mark.integration
def test_admin_user_page_with_login():

    do_login_as_admin()

    _ = test.get(ADMIN_HOME_URI, status=HTTP_OK)
    nav_links = [
        # header_buttons
        EDIT_URI.format(ADMIN_USER, 'fixtures', 'author'),
        EDIT_URI.format(ADMIN_USER, '_', 'index'),  # <-- New article
        EDITOR_URI,
        LOGOUT_URI,
        # footer_buttons
        "/export-archive/{:s}".format(ADMIN_USER),
    ]
    for href in nav_links:
        assert _.lxml.xpath(match_link(href))


@pytest.mark.integration
def test_create_index():
    """
    Creating an article should result in accurate metadata.
    """

    do_login_as_admin()

    index = trim("""
        Test Article

        = My important message!

        $ AUTHOR = Author Name
        $ DATE = 31 December 1999

        ` Part One
        ` Part Two
        """)
    doc_slug = 'test-article'
    clicks_on_preview = {
        'content': index,
        'they_selected_preview': 'YES',
    }

    uri = EDIT_URI.format(ADMIN_USER, '_', 'index')
    _ = test.post(uri, clicks_on_preview, status=HTTP_OK)  # Preview
    assert _.lxml.xpath("count(//h1)") == 1

    clicks_on_save = {
        'content': index,
        'they_selected_save': 'YES',
    }

    uri = EDIT_URI.format(ADMIN_USER, '_', 'index')
    new_uri = READ_URI.format(ADMIN_USER, 'test-article')

    _ = test.post(uri, clicks_on_save, status=HTTP_REDIRECT)  # Save
    assert _.headers['location'].endswith(new_uri)

    # Page should have article and links.
    _ = test.get(new_uri, status=HTTP_OK)
    assert "Test Article" in _
    assert "My important message!" in _
    assert "Author Name" in _
    nav_links = [
        ADMIN_HOME_URI,
        EDIT_URI.format(ADMIN_USER, doc_slug, 'index'),
        EDIT_URI.format(ADMIN_USER, doc_slug, 'biblio'),
        "/upload/{:s}/{:s}".format(ADMIN_USER, doc_slug),
        "/download/{:s}/{:s}".format(ADMIN_USER, doc_slug),
    ]
    for href in nav_links:
        assert _.lxml.xpath(match_link(href))

    # Check Latest Changes on the user page has the new article.

    _ = test.get(ADMIN_HOME_URI, status=HTTP_OK)
    assert 'Test Article' in _
    assert 'My important message!' in _
    assert '31 December 1999' in _


@pytest.mark.integration
def test_rename_article():

    do_login_as_admin()

    index_renamed = trim("""
        Test Article Renamed

        = My important message!

        ` Part One
        ` Part Two
        """)

    clicks_on_save = {
        'content': index_renamed,
        'they_selected_save': 'YES',
    }

    old_part = 'test-article'
    new_part = 'test-article-renamed'

    uri = EDIT_URI.format(ADMIN_USER, old_part, 'index')
    old_uri = READ_URI.format(ADMIN_USER, old_part)
    new_uri = READ_URI.format(ADMIN_USER, new_part)

    _ = test.post(uri, clicks_on_save, status=HTTP_REDIRECT)
    assert _.headers['location'].endswith(new_uri)

    _ = test.get(old_uri, status=HTTP_NOT_FOUND)
    _ = test.get(new_uri, status=HTTP_OK)

    # New URI must be linked in Latest Changes.
    _ = test.get(ADMIN_HOME_URI)
    assert _.lxml.xpath(match_link(new_uri))


@pytest.mark.integration
def test_create_part():

    do_login_as_admin()

    part_one = trim("""
        Test Article

        The text for today.

        ` Part One
        """)
    clicks_on_save = {
        'content': part_one,
        'they_selected_save': 'YES',
    }

    new_slug = 'test-article'

    uri = EDIT_URI.format(ADMIN_USER, '_', 'index')
    new_uri = READ_URI.format(ADMIN_USER, new_slug)

    _ = test.post(uri, clicks_on_save, status=HTTP_REDIRECT)
    assert _.headers['location'].endswith(new_uri)

    part_one = trim("""
        Part One

        ^[Example Link]

        ^ https://example.com
        """)
    clicks_on_save = {
        'content': part_one,
        'they_selected_save': 'YES',
    }

    uri = EDIT_URI.format(ADMIN_USER, 'test-article', '_')
    new_uri = READ_URI.format(ADMIN_USER, new_slug)

    _ = test.post(uri, clicks_on_save, status=HTTP_REDIRECT)
    assert _.headers['location'].endswith(new_uri)

    _ = test.get(new_uri, status=HTTP_OK)
    assert 'Example Link' in _
    assert 'https://example.com' in _
