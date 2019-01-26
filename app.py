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

from copy import copy
from datetime import datetime

import codecs
import logging
import pprint
import os
import sys
import tempfile

import bottle

from bottle_utils import flash

from beaker.middleware import SessionMiddleware
from jinja2 import Environment as JinjaTemplates, PackageLoader, escape
from slugify import slugify

from lib.data import Data, load_env_config
from lib.document import Document
from lib.storage import \
    compress_archive_dir, \
    make_tgz_name, \
    write_archive_dir
from lib.wiki.blocks import BlockList, get_title_data
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


def abs_url(request: bottle.BaseRequest, uri: str) -> str:
    """
    Prepend scheme/port/host to URI.
    """
    parts = request.urlparts
    # print(pprint.pformat(parts))
    return '{:s}://{:s}/{:s}'.format(parts.scheme, parts.netloc, uri.lstrip('/'))


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
    html = wiki.process({slug: copy(text), }, fragment=False, preview=True)
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
    # Single user mode means the admin user's homepage is the site home page.
    if config['SINGLE_USER'] == "YES":
        bottle.redirect('/user/{:s}'.format(data.admin_user))
    header_buttons = [playground_button(), help_button()]
    login = get_login()
    if login:
        header_buttons += [user_button(login['username'])]
        if login['is_admin'] in ['True', True]:
            header_buttons += [
                edit_button(login['username'], 'fixtures', 'homepage')
            ]
    else:
        header_buttons += [login_button(), playground_button()]
    article_list = data.userDocumentLastChanged_list()

    #  Show <admin-user>/fixtures/homepage:
    fixtures = data.userDocument_get(data.admin_user, 'fixtures')
    if isinstance(fixtures, dict) and 'homepage' in fixtures:
        document = {'index': fixtures['homepage']}
    else:
        document = {'index': trim("""
            Homepage

            (Text goes here...)
        """)}
    settings = Settings({
        'config:user': data.admin_user,
        'config:document': 'fixtures',
    })
    wiki = Wiki(settings)
    content_html = wiki.process(document)

    return views.get_template('home.html').render(
        config=config,
        header_buttons=header_buttons,
        article_list=article_list,
        content_html=content_html,
        pluralize=pluralize
    )


@bottle.get('/user/<user_slug>')
def user_page(user_slug):
    """
    Show <user_slug>/fixtures/author + user documents.
    """
    header_buttons = [login_or_logout_button(), playground_button()]
    login = get_login()
    if login and login['username'] == user_slug:
        header_buttons += [
            new_article_button(user_slug),
        ]
    header_buttons += [
        edit_button(user_slug, 'fixtures', 'author')
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
    content_html = wiki.process({'index': blocks.text()},
                                fragment=True,
                                preview=True)
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

    header_buttons = [home_button()]
    header_buttons += [edit_button(user_slug, doc_slug, 'index')]

    footer_buttons = [biblio_button(user_slug, doc_slug)]
    if has_authority_for_user(user_slug):
        footer_buttons += [upload_button(user_slug, doc_slug)]
    footer_buttons += [download_button(user_slug, doc_slug)]

    settings = Settings({
        'config:user': user_slug,
        'config:document': doc_slug,
    })

    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)

    html = data.userDocumentCache_get(user_slug, doc_slug)
    if not html or not metadata:
        wiki = Wiki(settings)
        doc_parts = require_document(user_slug, doc_slug)
        html = wiki.process(doc_parts)
        data.userDocumentCache_set(user_slug, doc_slug, html)
        metadata = wiki.compile_metadata(config.TIME_ZONE, user_slug, doc_slug)
        metadata['url'] = '/read/{:s}/{:s}'.format(user_slug, doc_slug),
        data.userDocumentMetadata_set(user_slug, doc_slug, metadata)

    uri = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
    metadata['url'] = abs_url(bottle.request, uri)
    author_uri = '/user/{:s}'.format(user_slug)
    metadata['author_url'] = abs_url(bottle.request, author_uri)
    metadata['home_url'] = abs_url(bottle.request, '/')
    metadata['image_url'] = abs_url(bottle.request, '/static/site-image.png')

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


@bottle.get('/export-archive/<user_slug>')
def export_archive(user_slug):
    """
    Creates an archive tarfile for download.

    @todo: Import archive!
    """
    require_user(user_slug)  # else 404
    tgz_name = make_tgz_name(user_slug)
    with tempfile.TemporaryDirectory() as dir_path:
        archive_data = data.userDocument_hash(user_slug)
        write_archive_dir(archive_data, dir_path)
        compress_archive_dir(dir_path, tgz_name)
        return bottle.static_file(tgz_name, root=dir_path, download=tgz_name)


@bottle.get('/download/<user_slug>/<doc_slug>')
def download_txt(user_slug, doc_slug):
    """
    Creates a single text file to download.
    """
    document = Document(data)
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
    prefix = '{:s}_{:s}_'.format(user_slug, doc_slug)
    if not name.startswith(prefix) or not name.endswith('.txt'):
        msg = "A '{:s}*.txt' file is required."
        bottle.abort(msg.format(prefix))

    # Load contents
    filepath = '/tmp/' + upload.filename
    if os.path.exists(filepath):
        os.unlink(filepath)
    upload.save('/tmp')
    try:
        contents = codecs.open(filepath, 'r', 'utf-8').read()
    except BaseException:
        msg = "Failed to read path '{:s}'."
        bottle.abort(HTTP_NOT_FOUND, msg.format(user_slug))
    os.unlink(filepath)

    document = Document(data)
    document.import_txt_file(user_slug, doc_slug, contents)
    document.save()

    uri = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
    bottle.redirect(uri)


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
        'href': 'http://github.com/eukras/article-wiki',
        'icon': 'github'
    }


# ---
# RUN
# ---


def main():
    bottle.run(host=config['WEB_HOST'], port=config['WEB_HOST_PORT'])


if __name__ == "__main__":
    main()
