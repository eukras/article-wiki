#!/usr/bin/python

"""
Article Wiki: A web reader and editor for long articles.

Article Wiki considers an article to be a collection of named wiki text
sections: {slug: text, ...}. The slugs are usually made from the titles, but
thius ccan be overridden. These can be files in a directory, or simply a Python
dictionary.  They are organised by an `index` part which contains a table of
contents.
"""

# -----
# SETUP
# -----

from cachetools.func import ttl_cache
from copy import copy
from datetime import datetime
# from dateutil.relativedelta import relativedelta
from feedgen.feed import FeedGenerator
from nltk import tokenize

import urllib.parse

import codecs
import dateutil
import difflib
import hmac
import io
# import json
import logging
import os
# import pickle
# import pprint
import sys
import tempfile

import bottle

from PIL import Image, ImageDraw
from bottle_utils import flash

from beaker.middleware import SessionMiddleware
from jinja2 import Environment as JinjaTemplates, PackageLoader
from markupsafe import escape
from slugify import slugify

from lib.bokeh import make_background
from lib.data import Data, load_env_config
from lib.document import Document
from lib.ebook import write_epub
from lib.overlay import make_cover, make_card, make_quote
from lib.storage import \
    compress_archive_dir, \
    make_zip_name, \
    write_archive_dir
from lib.wiki.blocks import BlockList, get_title_data
from lib.wiki.helpers import web_buttons
from lib.wiki.inline import Inline
from lib.wiki.settings import Settings
from lib.wiki.wiki import \
    Wiki, \
    clean_text, \
    is_index_part, \
    reformat_part, \
    split_published
from lib.wiki.utils import pluralize, trim


HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404

HASH = 97586

config = load_env_config()

if "pytest" in sys.modules:
    logging.info("Running in PyTest: Reconfiguring to use test database.")
    config['REDIS_DATABASE'] = config['REDIS_TEST_DATABASE']

# Redis, Jinja
data = Data(config)
views = JinjaTemplates(
    loader=PackageLoader('app', 'views'),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True
)

# Sessions
bottleApp = bottle.app()
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': config['COOKIE_SECRET'],
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}
bottleApp = SessionMiddleware(bottleApp, session_opts)

# Bottle plugins
bottle.install(flash.message_plugin)


@bottle.hook('before_request')
def before_request():
    """
    If a theme is set, make sure the views know about it.
    """
    theme = bottle.request.get_cookie('article-wiki-theme')
    if isinstance(theme, str):
        views.globals['theme'] = theme
    else:
        views.globals['theme'] = "theme-default"


def abs_url(request, uri):
    """
    Prepend scheme/port/host to URI.
    """
    parts = request.urlparts
    return '{:s}://{:s}/{:s}'.format(
        parts.scheme, parts.netloc, uri.lstrip('/')
    )


def domain_name(request):
    """
    Prepend scheme/port/host to URI.
    """
    parts = request.urlparts
    return '{:s}://{:s}'.format(
        parts.scheme, parts.netloc
    )


# -------------------------------------------------------------
# AUTHENTICATION/AUTHORISATION
# - Adequate for SINGLE_USER mode in v.0.1.0; interim approach.
# -------------------------------------------------------------


def get_login():
    """Return user dict or None"""
    cookie_name = config['COOKIE_NAME']
    cookie_secret = config['COOKIE_SECRET']
    token = bottle.request.get_cookie(
        cookie_name,
        secret=cookie_secret,
        # digestmod=hashlib.sha256  # <-- Needs bottle 0.13, see pytest.ini
    )
    if isinstance(token, str):
        user = data.login_get(token)
        return user
    else:
        return None


def has_authority_for_user(user_slug: str):
    """Check the logged-in user has authority for the specified user."""
    login = get_login()
    if isinstance(login, dict):
        return any([
            login['is_admin'] in ['True', True],
            user_slug == login['username']
        ])
    return False


def require_login():
    """Require user is logged in."""
    login = get_login()
    if not login:
        bottle.abort(HTTP_UNAUTHORIZED, "Login required.")
    return login


def require_authority_for_user(user_slug: str):
    """Die if not authorised for user."""
    if not has_authority_for_user(user_slug):
        bottle.abort(HTTP_UNAUTHORIZED, "Unauthorized access")


def require_authority_for_admin():
    """Die if not authorised as admin."""
    require_authority_for_user(config['ADMIN_USER'])


def is_published(user_slug, doc_slug):
    """Check in metadata whether document is publicly visible"""
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if isinstance(metadata, dict):
        if metadata.get('publish', 'NO') == 'YES':
            return True
    return False


@bottle.get('/login')
def login_form():
    """
    Show the login form, if we're using local auth (not OAUTH).
    """
    template = views.get_template('login.html')
    header_buttons = [home_button()]
    message = bottle.request.message  # <-- Flash messages
    return template.render(
        title="Login",
        config=config,
        header_buttons=header_buttons,
        message=message
    )


@bottle.post('/login')
def do_login():
    """
    Create redis record and cookie for admin user.

    v.0.1.0 -- Sufficient for SINGLE_USER mode.
    """
    username = bottle.request.forms.get('username')
    password = bottle.request.forms.get('password')
    authorized = all([
        username == config['ADMIN_USER'],
        password == config['ADMIN_USER_PASSWORD'],
    ])
    if authorized:
        is_admin = 'True' if username == data.admin_user else 'False'
        token = data.login_set({
            'username': username,
            'is_admin': is_admin
        })
        cookie_name = config['COOKIE_NAME']
        cookie_secret = config['COOKIE_SECRET']
        bottle.response.set_cookie(
            cookie_name,
            token,
            secret=cookie_secret,
            # digestmod=hashlib.sha256,  # <-- Needs Bottle 0.13,
            #                                  see pytest.ini
            path='/',
            httponly=True
        )
        bottle.redirect('/')
    else:
        bottle.response.flash("Login failed.")
        bottle.redirect('/login')


@bottle.get('/logout')
def do_logout():
    """
    Destroy redis record for user login, and delete cookie.
    """
    cookie_name = config['COOKIE_NAME']
    cookie_secret = config['COOKIE_SECRET']
    token = bottle.request.get_cookie(
        cookie_name,
        secret=cookie_secret,
        # digestmod=hashlib.sha256  # <-- Needs bottle 0.13, see pytest.ini
    )
    data.login_delete(token)
    bottle.response.delete_cookie(cookie_name, path='/')
    bottle.redirect('/')


# ------
# EDITOR
# ------

def show_editor(source: str,
                user_slug: str = '',
                doc_slug: str = '',
                part_slug: str = '',
                is_preview: bool = False,
                can_be_saved: bool = False):
    """
    Common renderer for /playground and /edit/user_slug/doc_slug/part_slug.
    """
    settings = Settings({
        'config:host': domain_name(bottle.request),
        'config:user': user_slug,
        'config:document': doc_slug,
    })
    wiki = Wiki(settings)
    part_slug, title, title_slug, summary = get_title_data(source, part_slug)
    text = reformat_part(part_slug, source)
    if part_slug == '':
        slug = slugify(title)
    elif part_slug != 'index' and is_index_part(text):
        slug = 'index'
    elif part_slug == 'biblio':
        slug = 'biblio'
    else:
        slug = part_slug
    html = wiki.process(user_slug, doc_slug, {slug: copy(text), },
                        fragment=False, preview=True)
    template = views.get_template('editor.html')
    return template.render(
        page_title="Editing: {:s}".format(title),
        config=config,
        user_slug=user_slug,
        doc_slug=doc_slug,
        part_slug=part_slug,
        preview=html,
        source=escape(text),
        is_preview=is_preview,
        can_be_saved=can_be_saved
    )


@bottle.get('/playground')
def editor():
    """
    Show a wiki demo editor that can be used without a login, but has no option
    to save content.
    """
    source = ""
    if 'template' in bottle.request.query:
        template_slug = bottle.request.query.get('template', '')
        templates = data.userDocument_get(data.admin_user, 'templates')
        if isinstance(templates, dict) and template_slug in templates:
            source = templates[template_slug]
    fixtures = data.userDocument_get(data.admin_user, 'fixtures')
    if isinstance(fixtures, dict) and 'editor' in fixtures:
        source = fixtures['editor']
    if is_index_part(source):
        user_slug, doc_slug = '_', '_'
        part_slug = 'index'
    else:
        user_slug, doc_slug = '_', '_'
        part_slug = '_'
    return show_editor(source, user_slug, doc_slug, part_slug,
                       is_preview=False,
                       can_be_saved=False)


@bottle.post('/playground')
def editor_post():
    """
    The `/editor` will only preview wiki formatting, never save it.
    """
    if 'content' in bottle.request.forms:
        source = bottle.request.forms.content
    else:
        source = ''
    is_preview = 'they_selected_preview' in bottle.request.forms
    return show_editor(source, '_', '_', '_',
                       is_preview=is_preview,
                       can_be_saved=False)


# -------
# GENERAL
# -------


@bottle.get('/favicon.ico')
def favicon_file():
    return bottle.static_file('favicon.ico', root='static')


@bottle.get('/robots.txt')
def robots_file():
    return bottle.static_file('robots.txt', root='static')


@bottle.get('/static/<file_name>')
def static_files(file_name):
    return bottle.static_file(file_name, root='static')


@bottle.error(HTTP_BAD_REQUEST)
def error400(error: bottle.HTTPError):
    logging.exception(error.body)
    header_buttons = [home_button(), back_button()]
    template = views.get_template('error.html')
    return template.render(title="Error - Bad Request",
                           header_buttons=header_buttons,
                           config=config,
                           message=error.body)


@bottle.error(HTTP_UNAUTHORIZED)
def error401(error: bottle.HTTPError):
    logging.exception(error.body)
    header_buttons = [home_button(), login_button(), back_button()]
    template = views.get_template('error.html')
    return template.render(title="Error - Unauthorised Access",
                           header_buttons=header_buttons,
                           config=config,
                           message=error.body)


@bottle.error(HTTP_NOT_FOUND)
def error404(error: bottle.HTTPError):
    logging.exception(error.body)
    header_buttons = [home_button(), back_button()]
    template = views.get_template('error.html')
    return template.render(title='Error - Not Found',
                           header_buttons=header_buttons,
                           config=config,
                           message=error.body)

# ----
# HELP
# ----


@bottle.get('/help')
def help():
    """The admin user's 'help' page is the official source..."""
    bottle.redirect('/read/{:s}/help'.format(data.admin_user))


# --------------
# DATA FUNCTIONS
# --------------


def require_user(user_slug: str) -> dict:
    """Return user hash if possible, else abort 404."""
    user = data.user_get(user_slug)  # or None
    if not user:
        msg = "User '{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug))
    return user


def require_document(user_slug: str, doc_slug: str) -> dict:
    """Return document hash if possible, else abort 404."""
    document = data.userDocument_get(user_slug, doc_slug)  # or None
    if not document:
        msg = "Document '{:s}/{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug, doc_slug))
    return document


# -----------
# APPLICATION
# -----------

@bottle.get('/')
def home_page():
    """
    Load up "<admin_user>/fixtures/homepage"

    v.0.1.0 -- Unused until we support SINGLE_USER = NO.
    """
    # SINGLE_USER mode means the admin user's homepage is the site home page.
    bottle.redirect('/user/{:s}'.format(data.admin_user))


@bottle.get('/user/<user_slug>')
def user_page(user_slug):
    """
    Show <user_slug>/fixtures/author + user documents.
    """
    header_buttons = [login_or_logout_button()]
    login = get_login()
    if login and login['username'] == user_slug:
        header_buttons += [
            new_article_button(user_slug),
        ]

    header_buttons += [
        edit_button(user_slug, 'fixtures', 'author'),
    ]

    if not login:
        header_buttons += [
            subscribe_button(),
            rss_button(user_slug)
        ]

    footer_buttons = []
    if config['ARTICLE_WIKI_CREDIT'] == 'YES':
        footer_buttons += [source_button()]
    footer_buttons += [help_button()]
    if has_authority_for_user(user_slug):
        footer_buttons += [export_archive_button(user_slug)]

    slugs = data.userDocumentSet_list(user_slug)
    changes_list = data.userDocumentLastChanged_list(user_slug)

    if not has_authority_for_user(user_slug):
        # Show only those that have been published
        changes_list, __ = split_published(changes_list)

    article_slugs = [_ for _ in slugs if _ not in ['fixtures', 'templates']]
    article_keys = [
        data.userDocumentMetadata_key(user_slug, _)
        for _ in article_slugs
    ]
    article_list = sorted(
        data.get_hashes(article_keys),
        key=lambda _: _.get('title', '')
    )

    published_articles, unpublished_articles = split_published(article_list)
    if not has_authority_for_user(user_slug):
        unpublished_articles = []

    settings = Settings({
        'config:host': domain_name(bottle.request),
        'config:user': user_slug,
        'config:document': 'fixtures',
    })
    wiki = Wiki(settings)
    document = data.userDocument_get(user_slug, 'fixtures')
    if not document:
        msg = "User '{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug))
    if 'author' in document:
        text = document['author']
    else:
        text = trim("""
            Author Page

            (Author information to be added here...)
            """)

    blocks = BlockList(clean_text(text))
    page_title, page_summary = blocks.pop_titles()
    content_html = wiki.process(None, None, {'index': blocks.text()},
                                fragment=True, preview=True)
    inline = Inline()

    return views.get_template('user.html').render(
        config=config,
        user=user_slug,
        page_title="{:s} - {:s}".format(page_title, page_summary),
        title_html=inline.process(page_title),
        summary_html=inline.process(page_summary),
        header_buttons=header_buttons,
        footer_buttons=footer_buttons,
        changes_list=changes_list,
        published_articles=published_articles,
        unpublished_articles=unpublished_articles,
        content_html=content_html,
        pluralize=pluralize  # <-- hack function injection
    )


@bottle.get('/read/<user_slug>/<doc_slug>')
def read_document(user_slug, doc_slug):
    """
    Compile the complete html document.
    """

    header_buttons = [
        home_button(),
        edit_button(user_slug, doc_slug, 'index'),
    ]

    login = get_login()
    if not login:
        header_buttons += [
            subscribe_button(),
            rss_button(user_slug)
        ]

    footer_buttons = [biblio_button(user_slug, doc_slug)]
    if has_authority_for_user(user_slug):
        footer_buttons += [
            upload_button(user_slug, doc_slug)
        ]
    footer_buttons += [download_button(user_slug, doc_slug)]

    settings = Settings({
        'config:host': domain_name(bottle.request),
        'config:user': user_slug,
        'config:document': doc_slug,
    })

    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)

    html = data.userDocumentCache_get(user_slug, doc_slug)
    if not html or not metadata:
        wiki = Wiki(settings)
        doc_parts = require_document(user_slug, doc_slug)
        html = wiki.process(user_slug, doc_slug, doc_parts)
        data.userDocumentCache_set(user_slug, doc_slug, html)
        metadata = wiki.compile_metadata(
            config['TIME_ZONE'], user_slug, doc_slug)
        metadata['url'] = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
        data.userDocumentMetadata_set(user_slug, doc_slug, metadata)

    uri = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
    metadata['url'] = abs_url(bottle.request, uri)
    author_uri = '/user/{:s}'.format(user_slug)
    metadata['author_url'] = abs_url(bottle.request, author_uri)
    metadata['home_url'] = abs_url(bottle.request, '/')
    image_uri = '/image/card/{:s}/{:s}.jpg'.format(user_slug, doc_slug)
    metadata['image_url'] = abs_url(bottle.request, image_uri)

    # @todo: function to split on multi authors as well as emails.
    title = metadata.get('title', 'Untitled')
    author = metadata.get('author', 'Anonymous')
    page_title = "{:s} - {:s}".format(title, author)

    template = views.get_template('read.html')
    template.trim_blocks = True
    template.lstrip_blocks = True
    page_html = template.render(
        config=config,
        page_title=page_title,
        metadata=metadata,
        user_slug=user_slug,
        doc_slug=doc_slug,
        web_buttons=web_buttons(user_slug, doc_slug),
        header_buttons=header_buttons,
        footer_buttons=footer_buttons,
        content_html=html
    )
    return page_html


@bottle.get('/edit/<user_slug>/<doc_slug>/<part_slug>')
def edit_part(user_slug, doc_slug, part_slug=None):
    """
    Open the editor to make changes to a doc_part
    """
    if not has_authority_for_user(user_slug):
        if not is_published(user_slug, doc_slug):
            msg = "Document '{:s}/{:s}' not found."
            bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug, doc_slug))
    if doc_slug == '_' and part_slug == 'index':
        if not has_authority_for_user(user_slug):
            msg = "You must be logged in to add a new document."
            bottle.abort(HTTP_UNAUTHORIZED, msg)
        today = datetime.now().strftime("%d %B %Y")
        part_text = trim("""
            ARTICLE_TITLE

            $ AUTHOR = AUTHOR_NAME
            $ EMAIL = AUTHOR_EMAIL
            $ FACEBOOK = FACEBOOK_USER
            $ TWITTER = TWITTER_USER
            $ DATE = PUBLICATION_DATE
            $ PUBLISH = NO

            + Summary

            > ARTICLE_SUMMARY

            % Comment: Create new article sections by adding them
            % to the Table of Contents here:

            ` Part One
            ` ` Section A
            ` Part Two
        """.replace('PUBLICATION_DATE', today))
        return show_editor(part_text, user_slug, doc_slug, part_slug,
                           is_preview=False,
                           can_be_saved=has_authority_for_user(user_slug))
    else:
        doc_parts = data.userDocument_get(user_slug, doc_slug)
        if not doc_parts:
            msg = "Document '{:s}/{:s}' not found."
            bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug, doc_slug))
        if part_slug in doc_parts:
            part_text = doc_parts[part_slug]
            return show_editor(part_text, user_slug, doc_slug, part_slug,
                               is_preview=False,
                               can_be_saved=has_authority_for_user(user_slug)
                               )
        else:
            params = bottle.request.query.decode()
            title = params['title'] if 'title' in params else 'New Section'
            part_slug = slugify(title)
            default = trim("""
                {:s}

                - Shortcuts!

                When editing, the following operations may save time.

                CENTER (80%) ---
                | Ctrl-SPACE | Select the current paragraph
                ---
                """.format(title))
            can_be_saved = has_authority_for_user(user_slug)
            return show_editor(default, user_slug, doc_slug, part_slug,
                               is_preview=False,
                               can_be_saved=can_be_saved)


@bottle.post('/edit/<user_slug>/<doc_slug>/<part_slug>')
def post_edit_part(user_slug, doc_slug, part_slug):
    """
    Wiki editor for existing doc part (or '_' if new).
    """
    if user_slug == '_':  # New user
        msg = "Blank user '_' not supported."
        bottle.abort(HTTP_BAD_REQUEST, msg)
    if doc_slug == '_' and part_slug == '_':
        msg = "Blank document and part '_/_' not supported."
        bottle.abort(HTTP_BAD_REQUEST, msg)

    if 'they_selected_save' in bottle.request.forms:
        require_authority_for_user(user_slug)
    if 'content' not in bottle.request.forms:
        bottle.abort(HTTP_BAD_REQUEST, "Form data was missing.")

    new_text = clean_text(bottle.request.forms.content)

    # Default slugs unless we change them
    new_part_slug = part_slug
    new_doc_slug, old_doc_slug = doc_slug, doc_slug

    document = Document(data)
    host = domain_name(bottle.request)
    document.set_host(host)
    if doc_slug == "_":
        # New article...
        new_doc_slug = document.set_index(new_text)
        new_doc_slug = data.userDocument_unique_slug(user_slug, new_doc_slug)
        document.set_slugs(user_slug, new_doc_slug)
    elif document.load(user_slug, doc_slug):
        if part_slug == 'index':
            new_doc_slug = document.set_index(new_text)
            if new_doc_slug != doc_slug:
                unique_slug = data.userDocument_unique_slug(user_slug,
                                                            new_doc_slug)
                document.set_slugs(user_slug, unique_slug)
        else:
            new_part_slug = document.set_part(part_slug, new_text)
    else:
        msg = "Document '{:s}/{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug, doc_slug))

    okay_to_save = all([
        'they_selected_save' in bottle.request.forms,
        has_authority_for_user(user_slug)
    ])

    if okay_to_save:

        new_doc_slug = document.save(pregenerate=True)

        old_doc = Document(data)
        if old_doc.load(user_slug, old_doc_slug):
            if old_doc.doc_slug != new_doc_slug:
                old_doc.delete()

        # Special redirects when editing fixtures
        uri = '/read/{:s}/{:s}'.format(user_slug, new_doc_slug)
        if doc_slug == 'fixtures':
            if part_slug == 'homepage':
                uri = '/'
            elif part_slug == 'author':
                uri = '/user/{:s}'.format(user_slug)
        bottle.redirect(uri)

    is_preview = 'they_selected_preview' in bottle.request.forms

    return show_editor(new_text,
                       document.user_slug,
                       document.doc_slug,
                       new_part_slug,
                       is_preview,
                       can_be_saved=has_authority_for_user(user_slug))


@bottle.get('/delete/<user_slug>/<doc_slug>/<part_slug>')
def delete_part(user_slug, doc_slug, part_slug):
    """
    Delete a part from a document. Must be logged in, and be the owner.

    To Do:
        - Form and confirmation step?
        - Delete parts including unused?
    """
    require_authority_for_user(user_slug)  # or 401
    document = Document(data)
    document.set_host(domain_name(bottle.request))
    if not document.load(user_slug, doc_slug):
        msg = "Document '{:s}/{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug, doc_slug))
    document.delete_part(part_slug)
    if len(document.parts) > 0:
        document.save()
        bottle.redirect('/read/{:s}/{:s}'.format(user_slug, doc_slug))
    else:
        document.delete()
        bottle.redirect('/user/{:s}'.format(user_slug))

# -------------
# USER COMMENTS
# -------------


@bottle.post('/api/comments')
def post_comment():
    """
    Receive an HTTP POST of comment data; just dump/log to storage.
    """
    aw_login = get_login()
    user_slug = bottle.request.json['user_slug']
    doc_slug = bottle.request.json['doc_slug']
    original = bottle.request.json['original']
    changes = bottle.request.json['changes']
    comment = bottle.request.json['comment']
    contact = bottle.request.json['contact']
    is_edit = original != changes
    utc = datetime.utcnow()

    # Confirm user_slug/doc_slug
    require_user(user_slug)
    _ = require_document(user_slug, doc_slug)

    # validate or fail
    if (len(original) == 0 or len(original) > 2000):
        bottle.abort(HTTP_BAD_REQUEST, "Invalid original text")
    if (len(changes) == 0 or len(changes) > 2000):
        bottle.abort(HTTP_BAD_REQUEST, "Invalid changes")
    if (len(comment) == 0 or len(comment) > 2000):
        bottle.abort(HTTP_BAD_REQUEST, "Invalid comment")
    if (len(contact) == 0 or len(contact) > 2000):
        bottle.abort(HTTP_BAD_REQUEST, "Invalid contact")

    log_dict = {
        'time_created': utc.isoformat(),
        'time_reviewed': None,
        'aw_login': aw_login['username'] if aw_login else "",
        'user_slug': user_slug,
        'doc_slug': doc_slug,
        'original': original,
        'changes': changes if is_edit else "",
        'comment': comment,
        'contact': contact,
        'ip_address': bottle.request.environ.get('REMOTE_ADDR'),
        'google_tracker': bottle.request.get_cookie('_ga', ''),
    }
    data.userDocumentCommentZset_add(
        user_slug, doc_slug, log_dict, utc
    )


@bottle.get('/comments/<user_slug>/<doc_slug>/<start_str>/<end_str>')
def show_comments(user_slug, doc_slug, start_str, end_str):
    """
    Show comments unless too many
    """
    require_user(user_slug)  # else 404
    _ = require_document(user_slug, doc_slug)  # else 404
    require_authority_for_admin()  # else 403

    # Require valid dates:
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    except Exception:
        bottle.abort(HTTP_BAD_REQUEST, "Dates must be yyyy-mm-dd")

    # If too many comments, divide...
    total = data.userDocumentCommentZset_countBetweenDates(
        user_slug, doc_slug, start_dt, end_dt
    )
    if total > 1000 and start_dt != end_dt:
        bottle.abort(HTTP_BAD_REQUEST, "Too many comments in date range")
    else:
        comments_base = data.userDocumentCommentZset_findBetweenDates(
            user_slug, doc_slug, start_dt, end_dt
        )

        def decorate(comment):
            created_dt = dateutil.parser.parse(comment['time_created'])
            fmt = "%Y-%m-%d %H:%M:%S (%a)"
            comment['time_created_fmt'] = created_dt.strftime(fmt)
            comment['time_created_ts'] = created_dt.timestamp()
            if comment['changes'] == "":
                comment['diff_html'] = ""
            else:
                seq1 = tokenize.sent_tokenize(comment['original'])
                seq2 = tokenize.sent_tokenize(comment['changes'])
                d = difflib.HtmlDiff(tabsize=4, wrapcolumn=40)
                comment['diff_html'] = d.make_table(seq1, seq2)
            return comment

        comments = [decorate(comment) for comment in comments_base]

        header_buttons = [{
            'name': 'Back',
            'href': '/read/{:s}/{:s}'.format(user_slug, doc_slug),
            'icon': 'arrow-left'
        }]

        return views.get_template('comments.html').render(
            title="Comments on '%s'" % doc_slug,
            config=config,
            header_buttons=header_buttons,
            user_slug=user_slug,
            doc_slug=doc_slug,
            start_str=start_str,
            end_str=end_str,
            comments=comments,
        )


@bottle.get('/api/comment/delete/<user_slug>/<doc_slug>/<time_created_ts>')
def delete_comment(user_slug, doc_slug, time_created_ts):
    """
    Require the exact timestamp, incl. microseconds
    """
    require_user(user_slug)
    require_authority_for_user(user_slug)
    _ = require_document(user_slug, doc_slug)

    start_dt = end_dt = datetime.fromtimestamp(float(time_created_ts))
    data.userDocumentCommentZset_deleteForDate(
        user_slug, doc_slug, start_dt, end_dt
    )


# -------------------------------------------------------------
# IMPORT AND EXPORT FUNCTIONS
# -------------------------------------------------------------


@bottle.get('/export-archive/<user_slug>')
def export_archive(user_slug):
    """
    Creates an archive tarfile for download.

    @todo: Import archive!
    """
    config['DEBUG'] = 'YES'
    require_user(user_slug)  # else 404
    with tempfile.TemporaryDirectory() as dir_path:
        archive_data = data.userDocument_hash(user_slug)
        write_archive_dir(dir_path, archive_data)
        if 'DEBUG' in config:
            print(['FILE NAMES: ' + user_slug, os.listdir(dir_path)])
        zip_name = make_zip_name(user_slug)
        zip_path = os.path.join(dir_path, zip_name)
        compress_archive_dir(dir_path, zip_name)
        if os.path.exists(zip_path):
            return bottle.static_file(
                zip_name,
                root=dir_path,
                download=zip_name
            )
        else:
            logging.error("Download failed: " + zip_name)
            bottle.abort(HTTP_BAD_REQUEST, "Download failed.")


@bottle.get('/download/<user_slug>/<doc_slug>')
def download_txt(user_slug, doc_slug):
    """
    Creates a single text file to download.
    """
    document = Document(data)
    document.set_host(domain_name(bottle.request))
    if not document.load(user_slug, doc_slug):
        msg = "Document '{:s}' not found."
        bottle.abort(HTTP_NOT_FOUND, msg.format(doc_slug))
    file_name, text = document.export_txt_file()
    attach_as_file = 'attachment; filename="{:s}"'.format(file_name)
    bottle.response.set_header('Content-Type', 'text/plain')
    bottle.response.set_header('Content-Disposition', attach_as_file)
    return text


@bottle.get('/upload/<user_slug>/<doc_slug>')
def upload_txt_form(user_slug, doc_slug):
    """Show an upload form to upload a document."""
    require_authority_for_user(user_slug)  # else 401s
    header_buttons = [{
        'name': 'Back',
        'href': '/read/{:s}/{:s}'.format(user_slug, doc_slug),
        'icon': 'arrow-left'
    }]
    return views.get_template('upload.html').render(
        config=config,
        user_slug=user_slug,
        doc_slug=doc_slug,
        header_buttons=header_buttons,
    )


@bottle.post('/upload/<user_slug>/<doc_slug>')
def post_upload_txt(user_slug, doc_slug):
    """
    Create a document from an download file.
    @todo: Show a diff?
    """
    require_authority_for_user(user_slug)  # else 401s
    upload = bottle.request.files.get('upload')

    # Validation
    limit = int(config['UPLOAD_LIMIT_KB'])
    if upload.content_length > (limit * 1024):
        msg = "The uploaded file is too large (limit: {:d}K)."
        bottle.abort(msg.format(limit))
    name = upload.filename
    prefix = 'article-wiki_{:s}_{:s}_'.format(user_slug, doc_slug)
    if not name.startswith(prefix) or not name.endswith('.txt'):
        msg = "A '{:s}*.txt' filename is expected."
        bottle.abort(msg.format(prefix))

    # Load contents
    filepath = '/tmp/' + upload.filename
    if os.path.exists(filepath):
        os.unlink(filepath)
    upload.save('/tmp')
    try:
        contents = codecs.open(filepath, 'r', 'utf-8').read()
    except Exception:
        msg = "Failed to read path '{:s}'."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug))
    os.unlink(filepath)

    document = Document(data)
    host = domain_name(bottle.request)
    document.set_host(host)
    document.import_txt_file(user_slug, doc_slug, contents)
    document.save()

    uri = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
    bottle.redirect(uri)

# ----- - TODO: Add mobi as well; same process?


@bottle.get('/epub/<user_slug>/<doc_slug>')
def generate_epub(user_slug, doc_slug):
    """
    Generates, caches and downloads an .epub; use a 'generating' notice to say
    reload the page in 5s; uses a simple redis lock or queue to show a 'reload
    in 5s' note.
    """

    file_name = '%s_%s.epub' % (user_slug, doc_slug)

    if data.epubCache_exists(user_slug, doc_slug):

        # Serve

        attach_as_file = 'attachment; filename="{:s}"'.format(file_name)
        bottle.response.set_header('Content-Type', 'application/epub+zip')
        bottle.response.set_header('Content-Disposition', attach_as_file)
        try:
            return data.epubCache_get(user_slug, doc_slug)
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)  # <--not right, kill it
            bottle.abort(HTTP_NOT_FOUND, "Temporary error generating ebook")

    elif data.epubCachePlaceholder_exists(user_slug, doc_slug):

        # Show the reload-in-5-mins page

        back_button = {
            'name': 'Back',
            'href': '/read/{:s}/{:s}'.format(user_slug, doc_slug),
            'icon': 'arrow-left'
        }
        return views.get_template('reload.html').render(
            config=config,
            user_slug=user_slug,
            doc_slug=doc_slug,
            header_buttons=[back_button, home_button()],
            title="Generating..."
        )

    else:

        # Generate and cache; requests for a lot of simultaneous
        # books that must all be generated could slow this down; add
        # a job queue later if that becomes necessary.

        data.epubCachePlaceholder_set(user_slug, doc_slug)  # with expiry

        file_path = os.path.join('/tmp', file_name)
        write_epub(user_slug, doc_slug, file_path)

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
        else:
            logging.error("Download failed: " + file_path)
            bottle.abort(HTTP_BAD_REQUEST, "Download failed.")

        data.epubCache_set(user_slug, doc_slug, content)
        data.epubCachePlaceholder_delete(user_slug, doc_slug)

        attach_as_file = 'attachment; filename="{:s}"'.format(file_name)
        bottle.response.set_header('Content-Type', 'application/epub+zip')
        bottle.response.set_header('Content-Disposition', attach_as_file)
        try:
            return data.epubCache_get(user_slug, doc_slug)
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)  # <--not right, kill it
            bottle.abort(HTTP_NOT_FOUND, "Temporary error generating ebook")


# --------
# Buttons!
# --------


def login_or_logout_button() -> dict:
    return logout_button() if get_login() else login_button()


def login_button() -> dict:
    return {
        'name': 'Login',
        'href': '/login',
        'icon': 'user'
    }


def logout_button() -> dict:
    return {
        'name': 'Logout',
        'href': '/logout',
        'icon': 'user'
    }


def back_button() -> dict:
    return {
        'name': 'Go Back',
        'href': 'javascript:window.history.go(-1);',
        'icon': 'arrow-left'
    }


def home_button() -> dict:
    if config['SINGLE_USER'] == 'YES':
        uri = "/user/{:s}".format(data.admin_user)
    else:
        uri = '/'
    return {
        'name': 'Home',
        'href': uri,
        'icon': 'home'
    }


def help_button() -> dict:
    return {
        'name': 'Help',
        'href': '/read/{:s}/help'.format(data.admin_user),
        'icon': 'question-circle'
    }


def subscribe_button() -> dict:
    return {
        'name': 'News',
        'href': config.get('SUBSCRIBE_LINK', ''),
        'icon': 'envelope'
    }


def rss_button(user_slug) -> dict:
    return {
        'name': 'RSS',
        'href': '/rss/%s.xml' % user_slug,
        'icon': 'rss'
    }


def playground_button() -> dict:
    return {
        'name': 'Playground',
        'href': '/playground',
        'icon': 'pencil'
    }


def user_button(user_slug: str) -> dict:
    return {
        'name': user_slug,
        'href': '/user/{:s}'.format(user_slug),
        'icon': 'user'
    }


def new_article_button(user_slug: str) -> dict:
    return {
        'name': 'New Article',
        'href': '/edit/{:s}/_/index'.format(user_slug),
        'icon': 'plus',
    }


# def epub_button(user_slug: str, doc_slug: str) -> dict:
    # return {
    # 'name': '.Epub',
    # 'href': '/epub/{:s}/{:s}'.format(user_slug, doc_slug),
    # 'icon': 'download',
    # }


def edit_button(user_slug: str, doc_slug: str, part_slug: str) -> dict:
    return {
        'name': 'Edit',
        'href': '/edit/{:s}/{:s}/{:s}'.format(user_slug, doc_slug, part_slug),
        'icon': 'pencil',
    }


def biblio_button(user_slug: str, doc_slug: str) -> dict:
    return {
        'name': 'Biblio',
        'href': '/edit/{:s}/{:s}/biblio'.format(user_slug, doc_slug),
        'icon': 'pencil'
    }


def download_button(user_slug: str, doc_slug: str) -> dict:
    return {
        'name': 'Download',
        'href': '/download/{:s}/{:s}'.format(user_slug, doc_slug),
        'icon': 'download'
    }


def upload_button(user_slug: str, doc_slug: str) -> dict:
    return {
        'name': 'Upload',
        'href': '/upload/{:s}/{:s}'.format(user_slug, doc_slug),
        'icon': 'upload'
    }


def export_archive_button(user_slug: str) -> dict:
    return {
        'name': 'Archive',
        'href': '/export-archive/{:s}'.format(user_slug),
        'icon': 'download',
    }


def source_button() -> dict:
    return {
        'name': 'Source',
        'href': 'https://github.com/eukras/article-wiki',
        'icon': 'github'
    }

# -----
# ADMIN
# -----


@bottle.get('/admin/expire-cache')
def expire():
    """
    Expire caches
    """
    require_authority_for_admin()  # else 403
    data.epubCache_deleteAll()
    return "OK"

# -----
# TESTS
# -----


COVER_DIMENSIONS = (1600, 2200)
MEDIA_DIMENSIONS = (1200, 630)

COLOR_TEXT = (248, 248, 248)        # <-- Alabaster
COLOR_SHADOW = (154, 174, 154)      # <-- Some greeny gray thing
COLOR_BACKGROUND = (160, 184, 160)  # <-- Norway, Summer Green, Pewter


def send_image(image: ImageDraw):
    """
    Download image without streaming it
    """
    stream = io.BytesIO()
    image.save(stream, 'JPEG', quality=85)
    stream.seek(0)
    bottle.response.set_header('Content-Type', 'image/jpeg')
    return stream


@bottle.get('/image/cover/<user_slug>/<doc_slug>.jpg')
def generate_cover(user_slug: str, doc_slug: str):
    image = cache_generate_cover(user_slug, doc_slug)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_cover(user_slug: str, doc_slug: str):
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if metadata:
        image = make_background(COVER_DIMENSIONS, COLOR_BACKGROUND)
        image = make_cover(image, [
            metadata['title'],
            metadata['summary'],
            metadata['author'],
            metadata['date'],
        ], [
            COLOR_TEXT,
            COLOR_SHADOW
        ])
        return image
    else:
        bottle.abort(HTTP_BAD_REQUEST, "No metadata")


@bottle.get('/image/card/<user_slug>/<doc_slug>.jpg')
def generate_card(user_slug, doc_slug):
    image = cache_generate_card(user_slug, doc_slug)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_card(user_slug, doc_slug):
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if metadata:
        image = make_background(MEDIA_DIMENSIONS, COLOR_BACKGROUND)
        byline = bottle.request.urlparts.netloc
        image = make_card(
            image, [
                metadata['title'],
                metadata['summary'],
            ], [
                COLOR_TEXT,
                COLOR_SHADOW
            ],
            byline
        )
        return image
    else:
        bottle.abort(HTTP_BAD_REQUEST, "No metadata")


@bottle.get('/image/quote/<checksum>/<encoded>.jpg')
def generate_quote(checksum, encoded):
    image = cache_generate_quote(checksum, encoded)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_quote(checksum, encoded):

    decoded = urllib.parse.unquote_plus(encoded)
    key = bytes(config['APP_HASH'], 'utf-8')
    message = bytes(decoded, 'utf-8')
    required = hmac.new(key, message, 'sha224').hexdigest()[:16]
    if checksum != required:
        bottle.abort(HTTP_NOT_FOUND, "No image")

    image_path = os.path.join(os.getcwd(), 'resources/quote.png')
    byline = bottle.request.urlparts.netloc
    image = Image.open(image_path).convert('RGB')
    image = make_quote(
        image, [
            decoded,
        ], [
            COLOR_BACKGROUND,
            (238, 238, 238)
        ],
        byline
    )
    return image


@bottle.get('/rss/<user_slug>.xml')
def rss_latest(user_slug):
    content_type = 'application/rss+xml; charset=utf-8'
    bottle.response.set_header('Content-Type', content_type)
    return cache_rss_latest(user_slug)


@ttl_cache(ttl=3600)
def cache_rss_latest(user_slug):

    articles = data.userDocumentLastChanged_list(user_slug)
    netloc = bottle.request.urlparts.netloc

    fg = FeedGenerator()
    fg.id(abs_url(bottle.request, '/user/%s' % user_slug))
    fg.title('Nigel Chapman (%s)' % netloc)
    fg.subtitle('Long reads on Christian thought')  # <-- Set METADATA for this
    # fg.author( {'name':'Nigel Chapman','email':'nigel@chapman.id.au'} )
    fg.logo('https://%s/static/site-image.png' % (netloc))
    fg.link(href='https://%s' % netloc, rel='self')
    # fg.link(href='https://%s/rss/%s.xml' % (netloc, user_slug), rel='self')
    fg.language('en')
    fg.ttl(24 * 3600)

    for a in articles:
        fe = fg.add_entry()
        article_uri = 'read/%s/%s' % (a['user'], a['slug'])
        fe.id(abs_url(bottle.request, article_uri))
        fe.title(a['title'])
        fe.description(a['summary'])
        fe.link(href=abs_url(bottle.request, article_uri))
        fe.author(name=a['email'], email=a['author'])  # <-- Wierdly backwards
        fe.published(a['published_time'])

    feed_xml = fg.rss_str(pretty=True)
    return feed_xml


# ---
# RUN
# ---


def main():
    bottle.run(host=config['WEB_HOST'], port=config['WEB_HOST_PORT'])


if __name__ == "__main__":
    main()
