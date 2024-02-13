#!/usr/bin/python

"""
Article Wiki: A web reader and editor for long articles.

Article Wiki considers an article to be a collection of named wiki text
sections: {slug: text, ...}. The slugs are usually made from the titles, but
this can be overridden. These can be files in a directory, a Redis hash, or
a Python dictionary. They are organised by an `index` part which contains a
table of contents.

- Account

@app.middleware('http') -- OK: Makes login available as a global.
@app.get('/login') -- OK: Login form.
@app.post('/login') -- OK: Stores a login token in a cookie.
@app.get('/logout') -- OK: Deletes the token cookie.

- Main pages

@app.get('/') -- OK: Redirects to admin user page
@app.get('/user/{user_slug}') -- OK: Shows user's fixtures/index page.
@app.get('/read/{user_slug}/{doc_slug}') -- OK: Shows user's doc_slug page.
@app.get('/rss/{user_slug}.xml') -- OK: Generate really simple XML.
@app.get('/help') -- OK: Shows admin user's 'help' document.

- Editing

@app.get('/edit/{user_slug}/{doc_slug}/{part_slug}') -- OK: Shows editor
@app.post('/edit/{user_slug}/{doc_slug}/{part_slug}') -- OK: Saves changes
@app.get('/playground') -- OK: Shows play editor.
@app.post('/playground') -- OK: Shows changes.
@app.get('/delete/{user_slug}/{doc_slug}/{part_slug}') -- OK.

- Import/Export

@app.get('/export-archive/{user_slug}') -- OK: Download a zipfile
@app.get('/import-archive/{user_slug}') -- OK: Show upload form
@app.post('/import-archive/{user_slug}') -- OK: Install a zipfile
@app.get('/download/{user_slug}/{doc_slug}') -- OK: Download a text file
@app.get('/upload/{user_slug}/{doc_slug}') -- OK: Show upload form
@app.post('/upload/{user_slug}/{doc_slug}') -- OK: Install a text file

- Generated content: ePubs and JPEGs

@app.get('/epub/{user_slug}/{doc_slug}') -- OK: Generates epub.
@app.get('/image/cover/{user_slug}/{doc_slug}.jpg') -- OK: Generates cover
@app.get('/image/card/{user_slug}/{doc_slug}.jpg') -- OK: Generates thumb
@app.get('/image/quote/{checksum}/{encoded}.jpg') -- OK: makes quote as image

- Special files; add sitemap?

@app.get('/favicon.ico') -- OK
@app.get('/robots.txt') -- OK

- Admin

@app.get('/admin/expire-cache') -- OK: deletes all cached docs for users
"""

# -----
# SETUP
# -----

from typing import Annotated

from cachetools.func import ttl_cache
from copy import copy
from datetime import datetime
from feedgen.feed import FeedGenerator

import urllib.parse

import hmac
import io
import json
import logging
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

# OLD SERVER w. BOTTLE

from jinja2 import Environment as JinjaTemplates, PackageLoader

from markupsafe import escape
from slugify import slugify

from fastapi import Depends, FastAPI, Form, HTTPException, status, \
    Request, UploadFile
from fastapi.responses import \
    HTMLResponse, \
    FileResponse, \
    PlainTextResponse, \
    RedirectResponse, \
    Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from lib.bokeh import make_background
from lib.data import Data, load_env_config
from lib.document import Document
from lib.ebook import write_epub
from lib.overlay import make_cover, make_card, make_quote
from lib.storage import \
    compress_archive_dir, \
    make_zip_name, \
    read_archive_dir, \
    uncompress_archive_dir, \
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
from lib.wiki.utils import trim


login = None
config = load_env_config()

if "pytest" in sys.modules:
    logging.info("Running in PyTest: Reconfiguring to use test database.")
    config['REDIS_DATABASE'] = config['REDIS_TEST_DATABASE']

app = FastAPI()

# Redis, Jinja
data = Data(config)
views = JinjaTemplates(
    loader=PackageLoader('main', 'views'),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True
)


# ----------------------------------------------------------
#                     Utility functions
# ----------------------------------------------------------

def abs_url(base_url: str, uri: str):
    """
    Prepend scheme/port/host to URI.
    """
    return base_url.rstrip('/') + '/' + uri.lstrip('/')


def domain_name(request: Request):
    """
    Prepend scheme/port/host to URI.
    """
    url = request.url
    return '{:s}://{:s}'.format(
        url.scheme, url.netloc
    )


def has_authority_for_user(user_slug: str):
    """Check the logged-in user has authority for the specified user."""
    if login is not None:
        return login['is_admin'] == 1 or user_slug == login['username']
    return False


def require_login():
    """Require user is logged in."""
    if not login:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Login required.")
    return login


def require_authority_for_user(user_slug: str):
    """Die if not authorised for user."""
    if not has_authority_for_user(user_slug):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Unauthorised.")


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


def require_user(user_slug: str) -> dict:
    """Return user hash if possible, else abort 404."""
    user = data.user_get(user_slug)  # or None
    if not user:
        msg = f"User '{user_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return user


def require_document(user_slug: str, doc_slug: str) -> dict:
    """Return document hash if possible, else abort 404."""
    document = data.userDocument_get(user_slug, doc_slug)  # or None
    if not document:
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return document


async def get_temp_dir():
    """
    Provide a temporary directory through dependency injection.
    """
    tmp_dir = tempfile.TemporaryDirectory()
    try:
        yield tmp_dir.name
    finally:
        del tmp_dir


# ----------------------------------------------------------
#                      Editor function
# ----------------------------------------------------------

def show_editor(source: str,
                domain_name: str,
                user_slug: str = '',
                doc_slug: str = '',
                part_slug: str = '',
                is_preview: bool = False,
                can_be_saved: bool = False):
    """
    Common renderer for /playground and /edit/user_slug/doc_slug/part_slug.
    """
    settings = Settings({
        'config:host': domain_name,
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
    html = template.render(
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
    return html


# ----------------------------------------------------------
#                       User Accounts
# ----------------------------------------------------------


@app.middleware("http")
async def set_login(request: Request, call_next):
    token = request.cookies.get('token', None)
    if token:
        global login  # <-- To change global.
        login = data.login_get(token)
    response = await call_next(request)
    return response


@app.get('/login')
async def login_form():
    """
    Show the login form, if we're using local auth (not OAUTH).
    """
    template = views.get_template('login.html')
    header_buttons = [home_button()]
    html = template.render(
        title="Login",
        config=config,
        header_buttons=header_buttons
    )
    return HTMLResponse(content=html)


@app.post('/login')
async def do_login(username: Annotated[str, Form()] = None,
             password: Annotated[str, Form()] = None):
    """
    Create redis record and cookie for admin user.

    v.0.1.0 -- Sufficient for SINGLE_USER mode.
    """
    authorized = all([
        username == config['ADMIN_USER'],
        password == config['ADMIN_USER_PASSWORD'],
    ])
    if authorized:
        token = data.login_set({
            'username': username,
            'is_admin': 1,
        })
        # 303 to change POST to GET:
        response = RedirectResponse('/', status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key='token', value=token)
        return response
    else:
        # bottle.response.flash("Login failed.")
        return RedirectResponse('/login',
                                status_code=status.HTTP_303_SEE_OTHER)


@app.get('/logout')
async def do_logout(request: Request):
    """
    Destroy redis record for user login, and delete cookie.
    """
    response = RedirectResponse('/')
    token = request.cookies.get('token', None)
    print('LOGOUT: token: ', token)
    if token:
        data.login_delete(token)
        response.delete_cookie(key='token')
        print('OK');
    return response


# ----------------------------------------------------------
#                        Main Pages
# ----------------------------------------------------------


@app.get('/')
async def home_page():
    """
    SINGLE_USER mode means the admin user's homepage is the site home page.
    """
    return RedirectResponse(f'/user/{data.admin_user}')


@app.get('/help')
async def help():
    """
    Show the admin user's 'help' page...
    """
    return RedirectResponse(f'/read/{data.admin_user}/help')


@app.get('/user/{user_slug}')
async def user_page(user_slug, request: Request):
    """
    Show /{user_slug}/fixtures/author.
    """
    header_buttons = [login_or_logout_button()]
    if login and login['username'] == user_slug:
        header_buttons += [
            new_article_button(user_slug),
        ]

    header_buttons += [
        edit_button(user_slug, 'fixtures', 'author'),
    ]

    footer_buttons = [help_button()]
    if config['ARTICLE_WIKI_CREDIT'] == 'YES':
        footer_buttons += [source_button()]
    if has_authority_for_user(user_slug):
        footer_buttons += [import_archive_button(user_slug)]
        footer_buttons += [export_archive_button(user_slug)]
    if not login:
        footer_buttons += [rss_button(user_slug)]

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
        'config:host': str(request.base_url),
        'config:user': user_slug,
        'config:document': 'fixtures',
    })
    wiki = Wiki(settings)

    document = data.userDocument_get(user_slug, 'fixtures')
    if not document:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_slug}' not found."
                )
    if 'author' in document:
        text = document['author']
    else:
        text = trim("""
            Author Page

            (Author information to be added here...)
            """)

    blocks = BlockList(clean_text(text))
    page_title, page_summary = blocks.title_and_summary()
    content_html = wiki.process('fixtures', 'author', {'index': blocks.text()},
                                fragment=False, preview=False)

    metadata = {
        'title': page_title,
    }

    inline = Inline()
    html = views.get_template('user.html').render(
        config=config,
        metadata=metadata,
        content_html=content_html,
        #   user=user_slug,
        #   page_title="{:s} - {:s}".format(page_title, page_summary),
        #   title_html=inline.process(page_title),
        #   summary_html=inline.process(page_summary),
        #   header_buttons=header_buttons,
        #   footer_buttons=footer_buttons,
        #   changes_list=changes_list,
        #   published_articles=published_articles,
        #   unpublished_articles=unpublished_articles,
        #   content_html=content_html,
        #   pluralize=pluralize  # <-- hack function injection
    )
    return HTMLResponse(content=html)


@app.get('/read/{user_slug}/{doc_slug}')
async def read_document(user_slug, doc_slug, request: Request):
    """
    Compile the complete html document.
    """

    settings = Settings({
        'config:host': str(request.base_url),
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
    metadata['url'] = abs_url(str(request.base_url), uri)
    author_uri = '/user/{:s}'.format(user_slug)
    metadata['author_url'] = abs_url(str(request.base_url), author_uri)
    metadata['home_url'] = abs_url(str(request.base_url), '/')
    image_uri = '/image/card/{:s}/{:s}.jpg'.format(user_slug, doc_slug)
    metadata['image_url'] = abs_url(str(request.base_url), image_uri)

    template = views.get_template('read.html')
    template.trim_blocks = True
    template.lstrip_blocks = True
    page_html = template.render(
        config=config,
        metadata=metadata,
        content_html=html
    )
    return HTMLResponse(content=page_html)


@app.get('/rss/{user_slug}.xml')
async def rss_latest(user_slug, request: Request):
    """
    Generate Really Simple Syndication data for recently edited files.
    """
    base_url = str(request.base_url)  # <-- URL type
    rss_xml = cache_rss_latest(user_slug, base_url)
    rss_xml_type = 'application/rss+xml; charset=utf-8'
    return Response(content=rss_xml,
                    media_type=rss_xml_type,
                    status_code=status.HTTP_200_OK)


@ttl_cache(ttl=3600)
def cache_rss_latest(user_slug, base_url):
    """
    Generate source data for RSS; separated to allow caching.
    """
    articles = data.userDocumentLastChanged_list(user_slug)
    fg = FeedGenerator()
    fg.id(abs_url(base_url, '/user/%s' % user_slug))
    fg.title('Nigel Chapman (%s)' % base_url)
    fg.subtitle('Long reads on Christian thought')  # <-- Set METADATA for this
    # fg.author( {'name':'Nigel Chapman','email':'nigel@chapman.id.au'} )
    fg.logo('https://%s/static/site-image.png' % (base_url))
    fg.link(href='https://%s' % base_url, rel='self')
    # fg.link(href='https://%s/rss/%s.xml' % (base_url, user_slug), rel='self')
    fg.language('en')
    fg.ttl(24 * 3600)

    for a in articles:
        fe = fg.add_entry()
        article_uri = 'read/%s/%s' % (a['user'], a['slug'])
        fe.id(abs_url(base_url, article_uri))
        fe.title(a['title'])
        fe.description(a['summary'])
        fe.link(href=abs_url(base_url, article_uri))
        fe.author(name=a['email'], email=a['author'])  # <-- Wierdly backwards
        fe.published(a['published_time'])

    feed_xml = fg.rss_str(pretty=True)
    return feed_xml


# ----------------------------------------------------------
#                           Editing
# ----------------------------------------------------------


@app.get('/edit/{user_slug}/{doc_slug}/{part_slug}')
async def edit_part(
        user_slug,
        doc_slug,
        part_slug=None,
        title: str = 'New Section',
        request: Request = None
        ):
    """
    Open the editor to make changes to a doc_part
    """
    domain = 'http://localhost:8000'
    if not has_authority_for_user(user_slug):
        if not is_published(user_slug, doc_slug):
            msg = f"Document '{user_slug}/{doc_slug}' not found."
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=msg)
    if doc_slug == '_' and part_slug == 'index':
        if not has_authority_for_user(user_slug):
            msg = "You must be logged in to add a new document."
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=msg)
        today = datetime.now().strftime("%d %B %Y")
        part_text = trim("""
            ARTICLE_TITLE

            $ AUTHOR = AUTHOR_NAME
            $ EMAIL = AUTHOR_EMAIL
            $ FACEBOOK = FACEBOOK_USER
            $ TWITTER = TWITTER_USER
            $ DATE = PUBLICATION_DATE
            $ PUBLISH = NO

            @ Summary

            > ARTICLE_SUMMARY

            % Comment: Create new article sections by adding them
            % to the Table of Contents here:

            - Part One
            - - Section A
            - Part Two
        """.replace('PUBLICATION_DATE', today))
        html = show_editor(part_text, domain, user_slug, doc_slug, part_slug,
                           is_preview=False,
                           can_be_saved=has_authority_for_user(user_slug))
        return HTMLResponse(content=html)
    else:
        doc_parts = data.userDocument_get(user_slug, doc_slug)
        if not doc_parts:
            msg = f"Document '{user_slug}/{doc_slug}' not found."
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=msg)
        if part_slug in doc_parts:
            part_text = doc_parts[part_slug]
            html = show_editor(part_text, domain, user_slug, doc_slug,
                               part_slug, is_preview=False,
                               can_be_saved=has_authority_for_user(user_slug))
            return HTMLResponse(content=html)
        else:
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
            html = show_editor(default, domain, user_slug, doc_slug, part_slug,
                               is_preview=False, can_be_saved=can_be_saved)
            return HTMLResponse(content=html)


@app.post('/edit/{user_slug}/{doc_slug}/{part_slug}')
async def post_edit_part(user_slug: str,
                         doc_slug: str,
                         part_slug: str,
                         content: Annotated[str, Form()] = None,
                         they_selected_save: Annotated[str, Form()] = None,
                         they_selected_preview: Annotated[str, Form()] = None,
                         request: Request = None):
    """
    Wiki editor for existing doc part (or '_' if new).
    """
    domain = str(request.base_url)
    if user_slug == '_':  # New user
        msg = "Blank user '_' not supported."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)
    if doc_slug == '_' and part_slug == '_':
        msg = "Blank document and part '_/_' not supported."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)

    if they_selected_save:
        require_authority_for_user(user_slug)
    if not content:
        msg = "Form data was missing"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)

    new_text = clean_text(content)

    # Default slugs unless we change them
    new_part_slug = part_slug
    new_doc_slug, old_doc_slug = doc_slug, doc_slug

    document = Document(data)
    host = str(request.base_url)
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
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    okay_to_save = all([
        they_selected_save is not None,
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
        return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)

    is_preview = they_selected_preview is not None

    html = show_editor(new_text,
                       domain,
                       document.user_slug,
                       document.doc_slug,
                       new_part_slug,
                       is_preview,
                       can_be_saved=has_authority_for_user(user_slug))
    return HTMLResponse(content=html)


@app.get('/playground')
def editor(request: Request, template: str | None = None):
    """
    Show a wiki demo editor that can be used without a login, but has no option
    to save content.
    """
    domain = str(request.base_url)
    source = ""
    if template:
        templates = data.userDocument_get(data.admin_user, 'templates')
        if isinstance(templates, dict) and template in templates:
            source = templates[template]
    else:
        fixtures = data.userDocument_get(data.admin_user, 'fixtures')
        if isinstance(fixtures, dict) and 'editor' in fixtures:
            source = fixtures['editor']
    if is_index_part(source):
        user_slug, doc_slug = '_', '_'
        part_slug = 'index'
    else:
        user_slug, doc_slug = '_', '_'
        part_slug = '_'
    html = show_editor(source, domain, user_slug, doc_slug, part_slug,
                       is_preview=False,
                       can_be_saved=False)
    return HTMLResponse(content=html)


@app.post('/playground')
def editor_post(request: Request,
                content: Annotated[str, Form()] = None,
                they_selected_preview: Annotated[str, Form()] = None):
    """
    The `/editor` will only preview wiki formatting, never save it.
    """
    domain = str(request.base_url)
    source = content or ''
    is_preview = they_selected_preview or False
    html = show_editor(source, domain, '_', '_', '_',
                       is_preview=is_preview,
                       can_be_saved=False)
    return HTMLResponse(content=html)


@app.get('/delete/{user_slug}/{doc_slug}/{part_slug}')
async def delete_part(user_slug, doc_slug, part_slug, request: Request):
    """
    Delete a part from a document. Must be logged in, and be the owner.

    To Do:
        - Form and confirmation step?
        - Delete parts including unused?
    """
    require_authority_for_user(user_slug)  # or 401
    document = Document(data)
    document.set_host(str(request.base_url))
    if not document.load(user_slug, doc_slug):
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    document.delete_part(part_slug)
    if len(document.parts) > 0:
        document.save()
        return RedirectResponse('/read/{:s}/{:s}'.format(user_slug, doc_slug))
    else:
        document.delete()
        return RedirectResponse('/user/{:s}'.format(user_slug))


# -------------------------------------------------------------
#                      Import / Export
# -------------------------------------------------------------


@app.get('/download/{user_slug}/{doc_slug}')
async def download_txt(user_slug, doc_slug, request: Request):
    """
    Creates a single text file to download.
    """
    document = Document(data)
    document.set_host(str(request.base_url))
    if not document.load(user_slug, doc_slug):
        msg = "Document '{:s}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    file_name, file_text = document.export_txt_file()
    file_headers = {
        'Content-Disposition': f'attachment; filename="{file_name}"'
    }
    return Response(content=file_text, media_type='text/plain',
                    headers=file_headers)


@app.get('/upload/{user_slug}/{doc_slug}')
async def upload_txt_form(user_slug, doc_slug):
    """Show an upload form to upload a document."""
    require_authority_for_user(user_slug)  # else 401s
    metadata = {
        'title': 'Upload a document'
    }
    content_html = views.get_template('upload.html').render(
        metadata=metadata,
        config=config,
        user_slug=user_slug,
        doc_slug=doc_slug,
    )
    return HTMLResponse(content=content_html)


@app.post('/upload/{user_slug}/{doc_slug}')
async def post_upload_txt(user_slug,
                          doc_slug,
                          upload: UploadFile,
                          request: Request):
    """
    Create a document from an download file.
    """
    require_authority_for_user(user_slug)  # else 401s

    limit_kb = int(config['UPLOAD_LIMIT_KB'])
    if upload.size > (limit_kb * 1024):
        msg = "The uploaded file is too large (limit: {limit_kb}K)."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)
    name = upload.filename
    prefix = 'article-wiki_{:s}_{:s}_'.format(user_slug, doc_slug)
    suffix = '.txt'
    print(name)
    if not name.startswith(prefix) or not name.endswith(suffix):
        msg = f"The filename must start with '{prefix}' and end with '{suffix}'"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)

    file_bytes = await upload.read()
    file_text = file_bytes.decode('utf-8')

    document = Document(data)
    host = str(request.base_url)
    document.set_host(host)
    document.import_txt_file(user_slug, doc_slug, file_text)
    document.save()

    uri = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


@app.get('/export-archive/{user_slug}')
async def export_archive(user_slug,
                         dir_path=Depends(get_temp_dir,
                                          use_cache=False)):
    """
    Processes an export_archive file based on upload settings.

    (FastAPI was losing its tempdir unless it was dynamically injected.)
    """
    require_user(user_slug)  # else 404
    archive_data = data.userDocument_hash(user_slug)
    write_archive_dir(dir_path, archive_data)
    zip_name = make_zip_name(user_slug)
    zip_path = os.path.join(dir_path, zip_name)
    compress_archive_dir(dir_path, zip_name)
    if os.path.exists(zip_path):
        return FileResponse(path=zip_path, filename=zip_name)
    else:
        msg = "Download failed: " + zip_name
        logging.error(msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)


@app.get('/import-archive/{user_slug}')
async def import_archive_form(user_slug):
    """
    Show import form for importing an archive zipfile.
    """
    require_authority_for_user(user_slug)  # else 401s
    header_buttons = [{
        'name': 'Back',
        'href': '/user/{:s}'.format(user_slug),
        'icon': 'arrow-left'
    }]
    html = views.get_template('import.html').render(
        config=config,
        user_slug=user_slug,
        header_buttons=header_buttons
    )
    return HTMLResponse(content=html)


@app.post('/import-archive/{user_slug}')
async def post_import_archive(user_slug,
                              upload: UploadFile,
                              request: Request,
                              dir_path=Depends(get_temp_dir,
                                               use_cache=False)):
    """
    Zaps the current user's data replaces it with a previously exported
    zipfile.

    Check permissions
    Get uploaded file
    Uncompress file
    Try to read into an archive_data file.
    If all OK:
        (Zap existing site data?)
        Install archive file
        Refresh metadata
        Regenerate the home page.
        Redirect to home
    Else:
        Show error
    """
    config['DEBUG'] = 'YES'
    require_authority_for_user(user_slug)  # else 401s

    name, ext = os.path.splitext(upload.filename)
    if ext != '.zip':
        logging.error("Bad uploaded file extension: " + ext)
        msg = "The upload must be a .zip file."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)

    file_path = os.path.join(dir_path, upload.filename)
    with open(file_path, 'w+b') as file:
        shutil.copyfileobj(upload.file, file)

    uncompress_archive_dir(dir_path, upload.filename)
    archive_data = read_archive_dir(dir_path)
    if 'DEBUG' in config:
        print(['FILE NAMES: ' + user_slug, archive_data.keys()])

    for doc_slug, doc_parts in archive_data.items():
        if len(doc_parts):
            settings = Settings({
                'config:host': str(request.base_url),
                'config:user': user_slug,
                'config:document': doc_slug,
            })
            wiki = Wiki(settings)
            html = wiki.process(user_slug, doc_slug, doc_parts)
            metadata = wiki.compile_metadata(config['TIME_ZONE'],
                                             user_slug, doc_slug)
            data.userDocument_set(user_slug, doc_slug, doc_parts, metadata)
            data.userDocumentCache_set(user_slug, doc_slug, html)
            metadata['url'] = '/read/{:s}/{:s}'.format(user_slug, doc_slug)
            data.userDocumentMetadata_set(user_slug, doc_slug, metadata)

    uri = f'/user/{user_slug}'
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


# ----------------------------------------------------------
# Buttons!  Remove these when converted to Airium.
# ----------------------------------------------------------


def login_or_logout_button() -> dict:
    return logout_button() if login else login_button()


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


def rss_button(user_slug) -> dict:
    return {
        'name': 'Changes (RSS)',
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
        'icon': 'arrow-down'
    }


def upload_button(user_slug: str, doc_slug: str) -> dict:
    return {
        'name': 'Upload',
        'href': '/upload/{:s}/{:s}'.format(user_slug, doc_slug),
        'icon': 'arrow-up'
    }


def export_archive_button(user_slug: str) -> dict:
    return {
        'name': 'Export',
        'href': '/export-archive/{:s}'.format(user_slug),
        'icon': 'arrow-down',
    }


def import_archive_button(user_slug: str) -> dict:
    return {
        'name': 'Import',
        'href': '/import-archive/{:s}'.format(user_slug),
        'icon': 'arrow-up',
    }


def source_button() -> dict:
    return {
        'name': 'Article Wiki',
        'href': 'https://github.com/eukras/article-wiki',
        'icon': 'github'
    }


# ----------------------------------------------------------
#                      Generated files
# ----------------------------------------------------------


@app.get('/epub/{user_slug}/{doc_slug}')
async def generate_epub(user_slug, doc_slug):
    """
    Generates, caches and downloads an .epub; use a 'generating' notice to say
    reload the page in 5s; uses a simple redis lock or queue to show a 'reload
    in 5s' note.
    """

    file_name = '%s_%s.epub' % (user_slug, doc_slug)

    if data.epubCache_exists(user_slug, doc_slug):

        try:
            zip_data = data.epubCache_get(user_slug, doc_slug)
            zip_data_type = 'application/epub+zip'
            zip_data_headers = {
                'Content-Disposition': f'inline; filename="{file_name}"'
            }
            return Response(content=zip_data,
                            media_type=zip_data_type,
                            headers=zip_data_headers)
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)
            data.epubCachePlaceholder_delete(user_slug, doc_slug)
            msg = "Temporary error generating ebook"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=msg)

    elif data.epubCachePlaceholder_exists(user_slug, doc_slug):

        # Show the reload-in-5-mins page

        back_button = {
            'name': 'Back',
            'href': '/read/{:s}/{:s}'.format(user_slug, doc_slug),
            'icon': 'arrow-left'
        }
        reload_html = views.get_template('reload.html').render(
            config=config,
            user_slug=user_slug,
            doc_slug=doc_slug,
            header_buttons=[back_button, home_button()],
            title="Generating..."
        )
        return HTMLResponse(content=reload_html, 
                            status_code=status.HTTP_202_ACCEPTED)

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
            msg = "Download failed"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=msg)

        data.epubCache_set(user_slug, doc_slug, content)
        data.epubCachePlaceholder_delete(user_slug, doc_slug)

        try:
            zip_data = data.epubCache_get(user_slug, doc_slug)
            zip_data_type = 'application/epub+zip'
            zip_data_headers = {
                'Content-Disposition': f'inline; filename="{file_name}"'
            }
            return Response(content=zip_data,
                            media_type=zip_data_type,
                            headers=zip_data_headers)
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)  # <-- Not right, rm
            msg = "Temporary error generating ebook"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=msg)

COVER_DIMENSIONS = (1600, 2200)
MEDIA_DIMENSIONS = (1200, 630)

COLOR_TEXT = (248, 248, 248)        # <-- Alabaster
COLOR_SHADOW = (154, 174, 154)      # <-- Some greeny gray thing
COLOR_BACKGROUND = (160, 184, 160)  # <-- Norway, Summer Green, Pewter


def send_image(image: ImageDraw):
    """
    Download image without streaming it
    """
    image_bytes = io.BytesIO()
    image.save(image_bytes, 'JPEG', quality=85)
    return Response(image_bytes.getvalue(), media_type='image/jpeg')


@app.get('/image/cover/{user_slug}/{doc_slug}.jpg')
def generate_cover(user_slug: str, doc_slug: str):
    image = cache_generate_cover(user_slug, doc_slug)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_cover(user_slug: str, doc_slug: str):
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if metadata:
        background = make_background(COVER_DIMENSIONS, COLOR_BACKGROUND)
        image = make_cover(background, [
            metadata['title'],
            metadata['summary'],
            metadata['author'],
            metadata['date'],
        ], [
            COLOR_TEXT,
            COLOR_SHADOW
        ])
        return image;
    else:
        raise HTTPException(content=status.HTTP_400_BAD_REQUEST, 
                            detail="No metadata")


@app.get('/image/card/{user_slug}/{doc_slug}.jpg')
def generate_card(user_slug, doc_slug, request: Request):
    base_url = str(request.base_url)  # <-- URL type
    image = cache_generate_card(user_slug, doc_slug, base_url)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_card(user_slug, doc_slug, base_url):
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if metadata:
        background = make_background(MEDIA_DIMENSIONS, COLOR_BACKGROUND)
        byline = base_url
        image = make_card(
            background, [
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
        msg = "No metadata"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)


@app.get('/image/quote/{checksum}/{encoded}.jpg')
def generate_quote(checksum, encoded):
    image = cache_generate_quote(checksum, encoded)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_quote(checksum, encoded, request: Request):
    """
    """
    base_url = str(request.base_url)  # <-- URL type
    decoded = urllib.parse.unquote_plus(encoded)
    key = bytes(config['APP_HASH'], 'utf-8')
    message = bytes(decoded, 'utf-8')
    required = hmac.new(key, message, 'sha224').hexdigest()[:16]
    if checksum != required:
        msg = "No image"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    image_path = os.path.join(os.getcwd(), 'resources/quote.png')
    byline = base_url
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


# ----------------------------------------------------------
#                Special files; add sitemap?
# ----------------------------------------------------------


@app.get('/favicon.ico')
async def favicon_file():
    return FileResponse(path='static/favicon.ico', filename='favicon.ico')


@app.get('/robots.txt')
async def get_language_file():
    return FileResponse(path='static/robots.txt', filename='robots.txt')


app.mount("/dist", StaticFiles(directory="dist"), name="dist")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ----------------------------------------------------------
#                      Administrative
# ----------------------------------------------------------

@app.get('/admin/expire-cache')
def expire():
    """
    Expire caches
    """
    require_authority_for_admin()  # else 403
    data.epubCache_deleteAll()
    return PlainTextResponse(content="OK")


# ----------------------------------------------------------
#                            Run
# ----------------------------------------------------------


def main():
    uvicorn.run('myapp:app', host='0.0.0.0', port=8000)


if __name__ == "__main__":
    main()
