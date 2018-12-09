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
import sys

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
    config['REDIS_DATABASE'] = "1"

data = Data(config)  # <-- DB 1 for tests
data.redis.flushdb()
data.login_create(config['ADMIN_USER'], config['ADMIN_USER_PASSWORD'])
load_fixtures()

test = AppTester(app.bottleApp)

if config['SINGLE_USER'] != 'YES':
    raise NotImplementedError("v. 0.1.0 does not implement multi-user mode.")


# -------------
# COMMON DATA
# -------------


editor_uri = '/editor'
help_uri = '/help'
home_uri = '/'
login_uri = '/login'
logout_uri = '/logout'
admin_home_uri = '/user/{:s}'.format(config['ADMIN_USER'])
admin_help_uri = '/read/{:s}/help'.format(config['ADMIN_USER'])

HTTP_OK = 200
HTTP_REDIRECT = 302
HTTP_NOT_FOUND = 404


# ------------
# 0. UTILITIES
# ------------


def do_logout():
    test.get(logout_uri)


def do_login_as_admin():
    login_page = test.get(login_uri)
    form = login_page.form
    form['username'] = config['ADMIN_USER']
    form['password'] = config['ADMIN_USER_PASSWORD']
    _ = form.submit()
    assert _.status_int == HTTP_REDIRECT  # Redirect
    assert _.headers['location'].endswith(home_uri)


def a_href(uri):
    """
    XPath to match an a.href attribute
    """
    return "//a[@href='{:s}']".format(uri)


# ---------------------------
# 1. NAVIGATION WITHOUT LOGIN
# ---------------------------


def test_homepage():
    """Main landing page."""
    do_logout()
    _ = test.get(home_uri)
    if config['SINGLE_USER'] == 'YES':
        assert _.status_int == HTTP_REDIRECT
        assert _.headers['location'].endswith(admin_home_uri)
    else:
        assert _.status_int == HTTP_REDIRECT
        assert _.headers['location'].endswith(home_uri)


def test_admin_user_page():
    """List admin user's articles, incl. link to help."""
    do_logout()
    _ = test.get(admin_home_uri)
    assert _.status_int == HTTP_OK
    nav_links = [
        admin_help_uri,
        editor_uri,
        login_uri,
    ]
    for href in nav_links:
        assert _.lxml.xpath(a_href(href))


def test_editor_page():
    """Editor page has buttons, textarea and main"""
    do_logout()
    _ = test.get(editor_uri)
    assert _.status_int == HTTP_OK
    assert _.lxml.xpath("//textarea")
    assert _.lxml.xpath("//main")


def test_help_page():
    # Help page (with standard lengthy content)
    do_logout()
    _ = test.get(help_uri)
    assert _.status_int == HTTP_REDIRECT
    assert _.headers['location'].endswith(admin_help_uri)
    _ = _.follow()  # <-- New response
    assert _.status_int == HTTP_OK
    assert _.lxml.xpath("count(//section)") > 30


def test_bad_login_fails():
    login_page = test.get(login_uri)
    form = login_page.form
    form['username'] = "Bad Username"
    form['password'] = "Wrong Password"
    _ = form.submit()
    assert _.status_int == HTTP_REDIRECT
    assert _.headers['location'].endswith(login_uri)

    # Issue with flash messaging in this test.
    # __ = _.follow()
    # assert __.status_int == HTTP_OK
    # assert "Login failed" in __


# ------------------------
# 2. NAVIGATION WITH LOGIN
# ------------------------


def test_admin_user_page_with_login():

    do_login_as_admin()

    _ = test.get(admin_home_uri)
    assert _.status_int == HTTP_OK
    nav_links = [
        # header_buttons
        "/edit/{:s}/fixtures/author".format(config['ADMIN_USER']),
        "/edit/{:s}/_/index".format(config['ADMIN_USER']),  # <-- New article
        editor_uri,
        logout_uri,
        # footer_buttons
        "/export-archive/{:s}".format(config['ADMIN_USER']),
    ]
    for href in nav_links:
        assert _.lxml.xpath(a_href(href))


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

    clicks_on_preview = {
        'content': index,
        'they_selected_preview': 'YES',
    }
    edit_uri = '/edit/{:s}/_/index'.format(data.admin_user)
    _ = test.post(edit_uri, clicks_on_preview)
    assert _.status_int == HTTP_OK
    assert _.lxml.xpath("count(//h1)") == 1

    clicks_on_save = {
        'content': index,
        'they_selected_save': 'YES',
    }

    new_uri = "/read/{:s}/test-article".format(config['ADMIN_USER'])
    edit_uri = '/edit/{:s}/_/index'.format(config['ADMIN_USER'])

    _ = test.post(edit_uri, clicks_on_save)
    assert _.status_int == HTTP_REDIRECT
    assert _.headers['location'].endswith(new_uri)

    # Page should have article and links.
    _ = test.get(new_uri)
    assert _.status_int == HTTP_OK
    assert "Test Article" in _
    assert "My important message!" in _
    assert "Author Name" in _
    nav_links = [
        admin_home_uri,
        "/edit/{:s}/test-article/index".format(config['ADMIN_USER']),
        "/edit/{:s}/test-article/biblio".format(config['ADMIN_USER']),
        "/upload/{:s}/test-article".format(config['ADMIN_USER']),
        "/download/{:s}/test-article".format(config['ADMIN_USER']),
    ]
    for href in nav_links:
        assert _.lxml.xpath(a_href(href))

    # Check Latest Changes on the user page has the new article.

    _ = test.get(admin_home_uri)
    assert _.status_int == HTTP_OK

    assert 'Test Article' in _
    assert 'My important message!' in _
    assert '31 December 1999' in _


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
    edit_uri = '/edit/{:s}/{:s}/index'.format(config['ADMIN_USER'], old_part)
    old_uri = '/read/{:s}/{:s}'.format(config['ADMIN_USER'], old_part)
    new_uri = '/read/{:s}/{:s}'.format(config['ADMIN_USER'], new_part)

    _ = test.post(edit_uri, clicks_on_save)
    assert _.status_int == HTTP_REDIRECT
    assert _.headers['location'].endswith(new_uri)

    _ = test.get(old_uri)
    assert _.status_int == HTTP_NOT_FOUND

    _ = test.get(new_uri)
    assert _.status_int == HTTP_OK

    _ = test.get(admin_home_uri)
    assert _.lxml.xpath(a_href(new_uri))


def test_create_part():

    do_login_as_admin()

    part_one = trim("""
        Part One

        The text for today.
        """)
    clicks_on_save = {
        'content': part_one,
        'they_selected_save': 'YES',
    }

    part_slug = 'test-article-renamed'
    edit_uri = '/edit/{:s}/{:s}/_'.format(config['ADMIN_USER'], part_slug)
    page_uri = '/read/{:s}/{:s}'.format(config['ADMIN_USER'], part_slug)

    _ = test.post(edit_uri, clicks_on_save)
    assert _.status_int == HTTP_REDIRECT

    _ = test.get(page_uri)
    assert _.status_int == HTTP_OK
    assert _.lxml.xpath(a_href('#1_part-one'))


def test_part_renaming():

    do_login_as_admin()

    part_one_renamed = trim("""
        Part One Renamed

        Ahoy!
        """)
    clicks_on_save = {
        'content': part_one_renamed,
        'they_selected_save': 'YES',
    }

    part_slug = 'test-article-renamed'
    edit_uri = '/edit/{:s}/{:s}/part-one'.format(config['ADMIN_USER'],
                                                 part_slug)
    page_uri = '/read/{:s}/{:s}/'.format(config['ADMIN_USER'], part_slug)

    _ = test.post(edit_uri, clicks_on_save)
    _ = test.get(page_uri)

    assert _.status_int == HTTP_OK
    assert _.lxml.xpath(a_href('#1_part-one-renamed'))
