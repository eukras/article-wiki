#!/usr/bin/python

"""
Article Wiki: A web reader and editor for long articles.

Article Wiki considers an article to be a collection of named wiki text
sections: {slug: text, ...}. The slugs are usually made from the titles, but
this can be overridden. These can be files in a directory, a Redis hash, or
a Python dictionary. They are organised by an `index` part which contains a
table of contents.

- Account

@app.middleware('http') -- Makes login available as a global.
@app.get('/login') -- Login form.
@app.post('/login') -- Stores a login token in a cookie.
@app.get('/logout') -- Deletes the token cookie.

- Main pages

@app.get('/') -- Redirects to admin user page
@app.get('/read/{user_slug}') -- Shows user's fixtures/index page.
@app.get('/read/{user_slug}/{doc_slug}') -- Shows user's doc_slug page.
@app.get('/rss/{user_slug}.xml') -- Generate really simple XML.
@app.get('/help') -- Shows admin user's 'help' document.

- Editing

@app.get('/new-article') -- Shows editor with template
@app.get('/edit/{user_slug}/{doc_slug}/{part_slug}') -- Shows editor
@app.post('/edit/{user_slug}/{doc_slug}/{part_slug}') -- Saves changes
@app.get('/playground') -- Shows play editor.
@app.post('/playground') -- Shows changes.
@app.get('/delete/{user_slug}/{doc_slug}/{part_slug}') -- Delete section

- Admin

@app.get('/admin') -- Administrative options:
@app.post('/admin/initialize') -- Load pages from install/articles directory
@app.post('/admin/regenerate') -- Regenerate all pages/metadata, cache them
@app.get('/admin/expire-cache') -- Deletes cached docs for users

- Import/Export as zifile

@app.get('/download.zip') -- Download a zipfile
@app.get('/download/{user_slug}.zip') -- Download a zipfile
@app.get('/download/{user_slug}/{doc_slug}.zip') -- Download a text file

@app.get('/upload') -- Show upload form
@app.get('/upload/{user_slug}') -- Show upload form
@app.get('/upload/{user_slug}/{doc_slug}') -- Show upload form

- Image handling

@app.post('/file/{user_slug}/{doc_slug}/{image_name}') -- Upload file (Admin)
@app.get('/file/{user_slug}/{doc_slug}/{image_name}') -- Display file

- Generated content: ePubs, JPEGs, SVG

@app.get('/sparkline/{user_slug}/{doc_slug}.svg') -- Generates sparkline.
@app.get('/epub/{user_slug}/{doc_slug}') -- Generates epub.
@app.get('/image/cover/{user_slug}/{doc_slug}.jpg') -- Generates cover
@app.get('/image/card/{user_slug}/{doc_slug}.jpg') -- Generates thumb
@app.get('/image/quote/{checksum}/{encoded}.jpg') -- makes quote as image

- Special files.

@app.get('/favicon.ico')
@app.get('/robots.txt')
"""

# -----
# SETUP
# -----

import hmac
import io
import logging
import os
import shutil
import sys
import tempfile
import uvicorn

from copy import copy
from datetime import datetime
from typing import Annotated
from urllib.parse import unquote_plus
from cachetools.func import ttl_cache
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment as JinjaTemplates
from jinja2 import PackageLoader
from markupsafe import escape
from PIL import Image
from PIL.Image import Image as ImageType

from command import initialize
from lib.archive import (
    Archive,
    user_document_zip_name,
    user_zip_name,
    zip_name,
)
from lib.bokeh import make_background
from lib.data import CONFIG, Data, IMAGE_DIMENSIONS, RedisTimer
from lib.document import PROTECTED_DOC_SLUGS, Document
from lib.ebook import write_epub
from lib.html_document import HtmlDocument
from lib.views import make_views
from lib.wiki.functions import base
from lib.wiki.halftone import apply_halftone
from lib.login import Login
from lib.overlay import make_card, make_cover, make_quote
from lib.rss import rss_xml
from lib.slugs import slug
from lib.sparkline import svg_sparkline
from lib.storage import (
    read_document_dir,
    read_user_dir,
    read_site_dir,
    uncompress_archive_dir,
)
from lib.typing import SiteUserDocuments, UserDocuments, DocumentParts
from lib.wiki.blocks import get_title_data
from lib.wiki.settings import Settings
from lib.wiki.utils import trim
from lib.wiki.wiki import Wiki, clean_text, is_index_part, reformat_part


if "pytest" in sys.modules:
    logging.info("Running in PyTest: Reconfiguring to use test database.")
    CONFIG["REDIS_DATABASE"] = CONFIG["REDIS_TEST_DATABASE"]

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Redis, Jinja
data = Data(CONFIG)
views = make_views()

# ----------------------------------------------------------
#                       Initialise DB
# ----------------------------------------------------------

if not data.user_exists(CONFIG["ADMIN_USER"]):
    initialize()


# -------------------------------------------------------------
#               Reusable Dependency Injections
# -------------------------------------------------------------

LoginDependency = Annotated[Login, Depends(use_cache=False)]
FormDependency = Annotated[str | None, Form()]


# ----------------------------------------------------------
#                     Utility functions
# ----------------------------------------------------------


def domain_name(request: Request):
    """
    Get the scheme ('https') and domain name ('chapman.wiki'),
    ready to add the URI ('/').
    """
    return f"{request.url.scheme}://{request.url.netloc}"


def is_published(user_slug: str, doc_slug: str) -> bool:
    """Check in metadata whether document is publicly visible"""
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if isinstance(metadata, dict):
        if metadata.get("publish", "NO") == "YES":
            return True
    return False


def require_zip(path: str):
    _, ext = os.path.splitext(path)
    if ext != ".zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The upload must be a .zip file.",
        )


def require_document(user_slug: str, doc_slug: str) -> dict:
    """Return document hash if possible, else abort 404."""
    document = data.userDocument_get(user_slug, doc_slug)  # or None
    if not document:
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return document


def refresh_site(base_url: str):
    """
    Ensure admin is refeshed last
    """
    for user_slug in data.non_admin_users():
        refresh_user(user_slug, base_url)
    refresh_user(CONFIG["ADMIN_USER"], base_url)


def refresh_user(user_slug: str, base_url: str):
    """
    Ensure index is refeshed last
    """
    for doc_slug in data.non_index_documents(user_slug):
        refresh_document(user_slug, doc_slug, base_url)
    refresh_document(user_slug, "index", base_url)


def refresh_document(user_slug: str, doc_slug: str, base_url: str):

    # Clear
    # data.userDocumentCache_delete(user_slug, doc_slug)
    # data.userDocumentMetadata_delete(user_slug, doc_slug)

    html_document = HtmlDocument(
        data,
        Wiki(
            Settings(
                {
                    "config:host": base_url,
                    "config:user": user_slug,
                    "config:document": doc_slug,
                }
            )
        ),
        views,
        CONFIG,
    )
    _ = html_document.generate(user_slug, doc_slug, base_url)


async def get_temp_dir():
    """
    Provide a temporary directory through dependency injection.

    @TODO: Process this in-memory, like for export.
    """
    tmp_dir = tempfile.TemporaryDirectory()
    try:
        yield tmp_dir.name
    finally:
        del tmp_dir


def clear_caches():
    data.userDocumentCache_deleteAll()
    data.epubCache_deleteAll()


def save_site(site_user_docs: SiteUserDocuments, config: dict):
    print(f"Saving {len(site_user_docs)} user...")
    for user_slug, user_docs in site_user_docs.items():
        if len(user_docs):
            save_user(user_slug, user_docs, config)


def save_user(user_slug, user_docs: UserDocuments, config: dict):
    print(f"  - Saving user {user_slug}: {len(user_docs)} docs...")
    for doc_slug, doc_parts in user_docs.items():
        if len(doc_parts):
            save_document(user_slug, doc_slug, doc_parts, config)


def save_document(
    user_slug: str, doc_slug: str, doc_parts: DocumentParts, config: dict
):
    print(f"      - Saving {user_slug}/{doc_slug} (x{len(doc_parts)})")

    doc = Document(data)
    doc.set_host(config["config:host"])
    doc.set_parts(user_slug, doc_slug, doc_parts)
    doc.save()

    text_parts = {key: part for key, part in doc_parts.items() if isinstance(part, str)}
    data.userDocument_set(user_slug, doc_slug, text_parts)

    image_parts = {
        key: part
        for key, part in doc_parts.items()
        if key in IMAGE_DIMENSIONS and isinstance(part, ImageType)
    }

    for file_name, image in image_parts.items():
        halftone = apply_halftone(image)
        data.userDocumentImage_set(user_slug, doc_slug, file_name, halftone)

    refresh_document(user_slug, doc_slug, config["config:host"])


# ----------------------------------------------------------
#                      Editor function
# ----------------------------------------------------------


def show_editor(
    source: str,
    domain_name: str,
    user_slug: str = "",
    doc_slug: str = "",
    part_slug: str = "",
    is_preview: bool = False,
    can_be_saved: bool = False,
):
    """
    Common renderer for /playground and /edit/user_slug/doc_slug/part_slug.
    """
    settings = Settings(
        {
            "config:host": domain_name,
            "config:user": user_slug,
            "config:document": doc_slug,
        }
    )
    wiki = Wiki(settings)
    part_slug, title, title_slug, summary = get_title_data(source, part_slug)
    text = reformat_part(part_slug, source)

    if part_slug == "":
        title_slug = slug(title)
    elif part_slug != "index" and is_index_part(text):
        title_slug = "index"
    elif part_slug == "biblio":
        title_slug = "biblio"
    else:
        title_slug = part_slug

    html = wiki.process(
        user_slug,
        doc_slug,
        {
            title_slug: copy(text),
        },
        fragment=False,
        preview=True,
        show_image=data.userDocumentImage_exists(user_slug, doc_slug, "title.png"),
    )

    template = views.get_template("editor.html")
    html = template.render(
        page_title=f"Editing: {title}",
        config=CONFIG,
        user_slug=user_slug,
        doc_slug=doc_slug,
        part_slug=part_slug,
        preview=html,
        source=escape(text),
        is_preview=is_preview,
        can_be_saved=can_be_saved,
    )
    return html


# ----------------------------------------------------------
#                       User Accounts
# ----------------------------------------------------------


@app.get("/login")
async def login_form():
    """
    Show the login form, if we're using local auth (not OAUTH).
    """
    template = views.get_template("login.html")
    html = template.render(
        title="Login",
        config=CONFIG,
    )
    return HTMLResponse(content=html)


@app.post("/login")
async def do_login(
    username: FormDependency,
    password: FormDependency,
):
    """
    Create redis record and cookie for admin user.
    """
    authorized = all(
        [
            username == CONFIG["ADMIN_USER"],
            password == CONFIG["ADMIN_USER_PASSWORD"],
        ]
    )
    if authorized:
        token = data.login_set(
            {
                "username": username,
                "is_admin": 1,
            }
        )
        # 303 to change POST to GET:
        response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="token", value=token)
        return response
    else:
        template = views.get_template("login.html")
        html = template.render(
            title="Login",
            message="Login failed.",
            config=CONFIG,
        )
        response = HTMLResponse(content=html)
        response.delete_cookie("token")
        return response


@app.get("/logout")
async def do_logout(request: Request):
    """
    Destroy redis record for user login, and delete cookie.
    """
    response = RedirectResponse("/")
    if token := request.cookies.get("token", None):
        data.login_delete(token)
        response.delete_cookie(key="token")
    return response


# ----------------------------------------------------------
#                        Error Pages
# ----------------------------------------------------------


def error_page(title, message):
    """
    Friendly recovery from an unexpected error.
    """
    template = views.get_template("error.html")
    page_html = template.render(
        title=title,
        message=message,
        config=CONFIG,
    )
    return HTMLResponse(content=page_html)


@app.exception_handler(403)
async def error_403(request: Request, exc: HTTPException) -> HTMLResponse:
    return error_page(
        title="Unauthorised",
        message="You need administrative priviliges to view this page.",
    )


@app.exception_handler(404)
async def error_404(
    request: Request, exc: HTTPException
) -> HTMLResponse | RedirectResponse:
    """
    If an article not found, check if admin user has that article.
    (This catches changes to admin user name.)
    """
    if all(
        [
            "user_slug" in request.path_params,
            "doc_slug" in request.path_params,
        ]
    ):
        admin_slug = CONFIG["ADMIN_USER"]
        doc_slug = slug(request.path_params["doc_slug"])
        if data.userDocument_exists(admin_slug, doc_slug):
            uri = f"/read/{admin_slug}/{doc_slug}"
            return RedirectResponse(uri, status_code=status.HTTP_308_PERMANENT_REDIRECT)

    return error_page(
        title="Not Found", message="This link does not match any page on this website."
    )


@app.exception_handler(500)
async def error_500(request: Request, exc: HTTPException) -> HTMLResponse:
    return error_page(
        title="System Error", message="This request could not be served at present."
    )


# ----------------------------------------------------------
#                        Main Pages
# ----------------------------------------------------------


@app.get("/")
async def home_page(
    request: Request,
):
    """
    If there is a '?shortcut' suffix, then see if we can find the shortcut.
    Otherwise just forward to the admin homepage.
    """
    empty_params = [key for key, value in request.query_params.items() if value == ""]
    if len(empty_params) > 0:
        for doc_slug in data.userDocumentSet_list(data.admin_user):
            metadata = data.userDocumentMetadata_get(data.admin_user, doc_slug)
            shortcut = metadata.get("shortcut", "")
            if shortcut == empty_params[0]:
                slug = metadata.get("slug")
                if slug:
                    return RedirectResponse(f"/read/{data.admin_user}/{slug}")
    return RedirectResponse(f"/read/{data.admin_user}/index")


@app.get("/help")
async def help():
    """
    Show the admin user's 'help' page...
    """
    return RedirectResponse(f"/read/{data.admin_user}/help")


@app.get("/read/{user_slug}/{doc_slug}")
async def read_document(user_slug, doc_slug, request: Request):
    """
    Compile the complete html document.
    """
    with RedisTimer(data, user_slug, doc_slug, "read"):
        html_document = HtmlDocument(
            data,
            Wiki(
                Settings(
                    {
                        "config:host": domain_name(request),
                        "config:user": user_slug,
                        "config:document": doc_slug,
                    }
                )
            ),
            views,
            CONFIG,
        )
        page_html = html_document.generate(user_slug, doc_slug, str(request.base_url))
    return HTMLResponse(content=page_html)


@app.get("/rss/{user_slug}.xml")
async def rss_latest(user_slug, request: Request):
    """
    Generate Really Simple Syndication data for recently edited files.
    """
    base_url = str(request.base_url)  # <-- URL type, so str()
    content = cache_rss_latest(user_slug, base_url)
    media_type = "application/rss+xml; charset=utf-8"
    return Response(
        content=content, media_type=media_type, status_code=status.HTTP_200_OK
    )


@ttl_cache(ttl=3600)
def cache_rss_latest(user_slug, base_url):
    """
    Generate source data for RSS; separated to allow caching.
    """
    articles = data.userDocumentLastChanged_list(user_slug)
    if feed_xml := rss_xml(user_slug, articles, base_url):
        return feed_xml
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="RSS feed unavailable"
        )


# ----------------------------------------------------------
#                           Editing
# ----------------------------------------------------------


@app.get("/new-article")
async def new_article(
    login: LoginDependency,
):
    if login is not None:
        uri = f"/edit/{login.username}/_/index"
        return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(
            content=status.HTTP_400_BAD_REQUEST,
            detail="You must login to create a new article",
        )


@app.get("/edit/{user_slug}/{doc_slug}/{part_slug}")
async def edit_part(
    user_slug,
    doc_slug,
    login: LoginDependency,
    part_slug=None,
    title: str = "New Section",
):
    """
    Open the editor to make changes to a doc_part
    """
    domain = CONFIG["SITE"]

    if not login.controls(user_slug) and not is_published(user_slug, doc_slug):
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    if doc_slug == "_" and part_slug == "index":
        if not login.controls(user_slug):
            msg = "You must be logged in to add a new document."
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
        today = datetime.now().strftime("%d %B %Y")
        part_text = trim(
            """
            ARTICLE_TITLE

            $ AUTHOR = AUTHOR_NAME
            $ EMAIL = AUTHOR_EMAIL
            $ SHORTCUT = shortcut
            $ DATE = PUBLICATION_DATE
            $ PUBLISH = NO

            @ Summary

            > ARTICLE_SUMMARY

            % Comment: Create new article sections by adding them
            % to the Table of Contents here:

            - Part One
            - - Section A
            - Part Two
        """.replace("PUBLICATION_DATE", today)
        )

        html = show_editor(
            part_text,
            domain,
            user_slug,
            doc_slug,
            part_slug,
            is_preview=False,
            can_be_saved=login.controls(user_slug),
        )
        return HTMLResponse(content=html)
    else:
        doc_parts = data.userDocument_get(user_slug, doc_slug)
        if not doc_parts:
            msg = f"Document '{user_slug}/{doc_slug}' not found."
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if part_slug in doc_parts:
            part_text = doc_parts[part_slug]
            html = show_editor(
                part_text,
                domain,
                user_slug,
                doc_slug,
                part_slug,
                is_preview=False,
                can_be_saved=login.controls(user_slug),
            )
            return HTMLResponse(content=html)
        else:
            part_slug = slug(title)
            default = trim(
                f"""
                {title}

                - Shortcuts!

                When editing, the following operations may save time.

                CENTER (80%) ---
                | Ctrl-SPACE | Select the current paragraph
                ---
                """
            )
            html = show_editor(
                default,
                domain,
                user_slug,
                doc_slug,
                part_slug,
                is_preview=False,
                can_be_saved=login.controls(user_slug),
            )
            return HTMLResponse(content=html)


@app.post("/edit/{user_slug}/{doc_slug}/{part_slug}")
async def post_edit_part(
    user_slug: str,
    doc_slug: str,
    part_slug: str,
    login: LoginDependency,
    content: FormDependency,
    they_selected_save: FormDependency = None,
    they_selected_preview: FormDependency = None,
    request: Request = None,
):
    """
    Wiki editor for existing doc part (or '_' if new).
    """
    if they_selected_save:
        login.require_control(user_slug)

    if user_slug == "_":  # New user
        msg = "Blank user '_' not supported."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    if doc_slug == "_" and part_slug == "_":
        msg = "Blank document and part '_/_' not supported."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    if not content:
        msg = "Form data was missing"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

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
        if part_slug == "index":
            new_doc_slug = document.set_index(new_text)
            if new_doc_slug != doc_slug:
                unique_slug = data.userDocument_unique_slug(user_slug, new_doc_slug)
                document.set_slugs(user_slug, unique_slug)
        else:
            new_part_slug = document.set_part(part_slug, new_text)
    else:
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    okay_to_save = all([they_selected_save is not None, login.controls(user_slug)])

    if okay_to_save:
        saved_doc_slug = document.save(pregenerate=True)
        if old_doc_slug not in PROTECTED_DOC_SLUGS:
            new_doc_slug = saved_doc_slug

        old_doc = Document(data)
        if old_doc.load(user_slug, old_doc_slug):
            if old_doc.doc_slug != new_doc_slug:
                old_doc.delete()

        uri = f"/read/{user_slug}/{new_doc_slug}"
        return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)

    is_preview = they_selected_preview is not None

    domain = str(request.base_url)

    html = show_editor(
        new_text,
        domain,
        document.user_slug,
        document.doc_slug,
        new_part_slug,
        is_preview,
        can_be_saved=login.controls(user_slug),
    )
    return HTMLResponse(content=html)


@app.get("/files/{user_slug}/{doc_slug}")
async def files(
    user_slug: str,
    doc_slug: str,
    login: LoginDependency,
):
    """
    Manage page files for user_slug/doc_slug.
    """

    if not login.controls(user_slug) and not is_published(user_slug, doc_slug):
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    html = views.get_template("article-files.html").render(
        user_slug=user_slug,
        doc_slug=doc_slug,
        config=CONFIG,
        dimensions=IMAGE_DIMENSIONS,
    )
    return HTMLResponse(content=html)


@app.post("/file-delete/{user_slug}/{doc_slug}/{file_name}")
async def files(
    user_slug: str,
    doc_slug: str,
    file_name: str,
    login: LoginDependency,
):
    """
    Manage page files for user_slug/doc_slug.
    """

    login.require_control(user_slug)
    require_accepted_filename(file_name)

    if not data.userDocumentImage_exists(user_slug, doc_slug, file_name):
        msg = f"File '{user_slug}/{doc_slug}/{file_name}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    data.userDocumentImage_delete(user_slug, doc_slug, file_name)

    uri = f"/read/{user_slug}/{doc_slug}"
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/playground")
def editor(request: Request, template: str | None = None):
    """
    Show a wiki demo editor that can be used without a login, but has no option
    to save content.
    """
    domain = str(request.base_url)
    source = """Article Wiki

= Welcome to the Playground

$ SLUG = editor

You can use this test page to experiment with wiki formatting. Or make one-off documents and print straight to PDF through your browser. Have a look at the ^[Help Page] to learn everything about the wiki markup.

^ https://chapman.wiki/read/eukras/help


+ Thought for the day

> It seems that perfection is attained not when there is nothing more to add, but when there is nothing more to remove.
= ~[de Saint Exupéry, /Terre des Hommes/, p.60]


- A little subheading

* Try bullet lists and quotations.
* Try ^[footnotes], #[index:indexes], and citations (see above).
* Try floats, alignment, columns, tables.

^ Here's a footnote!


_____

de Saint Exupéry, Antoine. 1939. Terre des Hommes. Paris: Éditions Gallimard.
    """

    if is_index_part(source):
        user_slug, doc_slug = "_", "_"
        part_slug = "index"
    else:
        user_slug, doc_slug = "_", "_"
        part_slug = "_"
    html = show_editor(
        source,
        domain,
        user_slug,
        doc_slug,
        part_slug,
        is_preview=False,
        can_be_saved=False,
    )
    return HTMLResponse(content=html)


@app.post("/playground")
def editor_post(
    request: Request,
    content: FormDependency = None,
    they_selected_preview: FormDependency = None,
):
    """
    The `/editor` will only preview wiki formatting, never save it.
    """
    domain = str(request.base_url)
    source = content or ""
    is_preview = they_selected_preview or False
    html = show_editor(
        source, domain, "_", "_", "_", is_preview=is_preview, can_be_saved=False
    )
    return HTMLResponse(content=html)


@app.get("/delete/{user_slug}/{doc_slug}/{part_slug}")
async def delete_part(
    user_slug: str,
    doc_slug: str,
    part_slug: str,
    request: Request,
    login: LoginDependency,
):
    """
    Delete a part from a document. Must be logged in, and be the owner.

    To Do:
        - Form and confirmation step?
        - Delete parts including unused?
    """
    login.require_control(user_slug)

    document = Document(data)
    document.set_host(str(request.base_url))
    if not document.load(user_slug, doc_slug):
        msg = f"Document '{user_slug}/{doc_slug}' not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    document.delete_part(part_slug)
    if len(document.parts) > 0:
        document.save()
        return RedirectResponse(f"/read/{user_slug}/{doc_slug}")
    else:
        document.delete()
        return RedirectResponse(f"/read/{user_slug}/index")


# -------------------------------------------------------------
#                       Administration
# -------------------------------------------------------------


@app.get("/admin")
async def admin(
    login: LoginDependency,
):
    """
    Show administrative options.
    """
    login.require_admin()
    html = views.get_template("admin-site.html").render(config=CONFIG)
    return HTMLResponse(content=html)


@app.post("/admin/initialize")
async def admin_initialize(
    login: LoginDependency,
    request: Request,
):
    """
    Reset site to starting configuration.
    """
    login.require_admin()
    initialize()

    # And logout
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    if token := request.cookies.get("token", None):
        data.login_delete(token)
        response.delete_cookie(key="token")

    return response


@app.post("/admin/refresh")
async def admin_refresh(
    login: LoginDependency,
    request: Request,
):
    """
    Regenerate, re-cache, and correct the metadata for all pages.
    """
    login.require_admin()
    refresh_site(str(request.base_url))
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


# -------------------------------------------------------------
#                       Image files
# -------------------------------------------------------------


def require_accepted_filename(file_name):
    if file_name not in IMAGE_DIMENSIONS.keys():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The filename must be one of {IMAGE_DIMENSIONS.keys()}, not file_name",
        )


def require_accepted_dimensions(file_name, image):
    if image.size != IMAGE_DIMENSIONS[file_name]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The file {file_name} must have the size {IMAGE_DIMENSIONS[file_name]}, not {image.size}",
        )


@app.post("/file/{user_slug}/{doc_slug}/{file_name}")
async def upload_file(
    user_slug: str,
    doc_slug: str,
    file_name: str,
    upload: UploadFile,
    # login: LoginDependency,
):
    """
    Replaces the current file_name with the new file.

    Check permissions
    Get uploaded file
    Store into document
    Stay on page
    """
    # login.require_control(user_slug)

    require_accepted_filename(file_name)

    image_data = upload.file.read()
    image = Image.open(io.BytesIO(image_data))
    image.load()  # load while in memory

    require_accepted_dimensions(file_name, image)

    halftone = apply_halftone(image)
    data.userDocumentImage_set(user_slug, doc_slug, file_name, halftone)

    # 303 to forward POST to GET
    return RedirectResponse(
        f"/files/{user_slug}/{doc_slug}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/file/{user_slug}/{doc_slug}/{file_name}")
async def display_image(
    user_slug: str,
    doc_slug: str,
    file_name: str,
):
    """
    /file/ is only used for document images.
    """
    require_accepted_filename(file_name)
    # if cache_bytes := data.userDocumentImageCache_get(user_slug, doc_slug, file_name):
    #     return send_image_bytes(cache_bytes)
    # else:
    if image := data.userDocumentImage_get(user_slug, doc_slug, file_name):
        return send_image(image)

    # else, not found
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# -------------------------------------------------------------
#            Import / Export (.zip for one article)
# -------------------------------------------------------------


@app.get("/download/{user_slug}/{doc_slug}.zip")
async def download_document_zip(user_slug, doc_slug):
    """
    Downloads an export_archive file.
    - Anyone can do this
    - Ignores whether a doc is published or not.
    """
    archive = Archive(data)
    zip_name = user_document_zip_name(user_slug, doc_slug)
    return Response(
        archive.zip_document(user_slug, doc_slug),
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": f'inline; filename="{zip_name}"',
        },
    )


@app.get("/upload/{user_slug}/{doc_slug}")
async def upload_document_form(
    user_slug: str,
    doc_slug: str,
    login: LoginDependency,
):
    """
    Show import form for importing an archive zipfile.
    """
    login.require_control(user_slug)

    html = views.get_template("upload.html").render(
        config=CONFIG,
        user_slug=user_slug,
        doc_slug=doc_slug,
        import_file=user_document_zip_name(user_slug, doc_slug),
    )
    return HTMLResponse(content=html)


@app.post("/upload/{user_slug}/{doc_slug}")
async def post_upload_document_form(
    user_slug,
    doc_slug,
    upload: UploadFile,
    request: Request,
    login: LoginDependency,
    dir_path=Depends(get_temp_dir, use_cache=False),
):
    """
    Zaps the current user's data replaces it with a previously exported
    zipfile.
    """
    login.require_control(user_slug)

    require_zip(upload.filename)

    file_path = os.path.join(dir_path, upload.filename)
    with open(file_path, "w+b") as file:
        shutil.copyfileobj(upload.file, file)
    uncompress_archive_dir(dir_path, upload.filename)
    archive_data = read_document_dir(dir_path)
    save_document(
        user_slug,
        doc_slug,
        archive_data,
        {
            "config:host": str(request.base_url),
        },
    )

    base_url = str(request.base_url)  # <-- URL type
    refresh_site(base_url)

    # 303 to forward POST to GET
    uri = f"/read/{user_slug}/index"
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


# -------------------------------------------------------------
#          Import / Export (.zip for a user's archive)
# -------------------------------------------------------------


@app.get("/download/{user_slug}.zip")
async def download_user_zip(user_slug):
    """
    Downloads an export_archive file.
    - Anyone can do this
    - Ignores whether a doc is published or not.
    """
    archive = Archive(data)
    zip_name = user_zip_name(user_slug)
    return Response(
        archive.zip_user(user_slug),
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": f'inline; filename="{zip_name}"',
        },
    )


@app.get("/upload/{user_slug}")
async def upload_user_form(
    user_slug: str,
    login: LoginDependency,
):
    """
    Show upload form for importing an archive zipfile.
    """
    login.require_control(user_slug)

    html = views.get_template("upload.html").render(
        config=CONFIG,
        user_slug=user_slug,
        import_file=user_zip_name(user_slug),
    )
    return HTMLResponse(content=html)


@app.post("/upload/{user_slug}")
async def post_upload_user_form(
    user_slug,
    upload: UploadFile,
    request: Request,
    login: LoginDependency,
    dir_path=Depends(get_temp_dir, use_cache=False),
):
    """
    Zaps the current user's data replaces it with a previously exported
    zipfile.
    """
    login.require_control(user_slug)

    _, ext = os.path.splitext(upload.filename)
    if ext != ".zip":
        logging.error("Bad uploaded file extension: " + ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The upload must be a .zip file.",
        )

    file_path = os.path.join(dir_path, upload.filename)
    with open(file_path, "w+b") as file:
        shutil.copyfileobj(upload.file, file)

    uncompress_archive_dir(dir_path, upload.filename)
    archive_data = read_user_dir(dir_path)
    save_user(
        user_slug,
        archive_data,
        {
            "config:host": str(request.base_url),
        },
    )

    # 303 to forward POST to GET
    uri = f"/read/{user_slug}/index"
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


# -------------------------------------------------------------
# Download/upload site
# -------------------------------------------------------------


@app.get("/download.zip")
async def download_site_zip():
    """
    Downloads an archive file.
    - Anyone can do this
    - Ignores whether a doc is published or not.
    """
    archive = Archive(data)
    file_name = zip_name()
    return Response(
        archive.zip_site(),
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": f'inline; filename="{file_name}"',
        },
    )


@app.get("/upload")
async def upload_site_form():
    """
    Show upload form for importing an archive zipfile.
    """
    html = views.get_template("upload.html").render(
        config=CONFIG,
        import_file=zip_name(),
    )
    return HTMLResponse(content=html)


@app.post("/upload")
async def post_upload_site_form(
    upload: UploadFile,
    request: Request,
    login: LoginDependency,
    dir_path=Depends(get_temp_dir, use_cache=False),
):
    """
    Zaps the current site's data replaces it with a previously exported
    zipfile.
    """
    login.require_admin()

    _, ext = os.path.splitext(upload.filename)
    if ext != ".zip":
        logging.error("Bad uploaded file extension: " + ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The upload must be a .zip file.",
        )

    file_path = os.path.join(dir_path, upload.filename)
    with open(file_path, "w+b") as file:
        shutil.copyfileobj(upload.file, file)

    uncompress_archive_dir(dir_path, upload.filename)
    archive_data = read_site_dir(dir_path)
    save_site(
        archive_data,
        {
            "config:host": str(request.base_url),
        },
    )

    # 303 to forward POST to GET
    uri = f"/read/{CONFIG['ADMIN_USER']}/index"
    return RedirectResponse(uri, status_code=status.HTTP_303_SEE_OTHER)


# ----------------------------------------------------------
#                      Generated files
# ----------------------------------------------------------


@app.get("/sparkline/{user_slug}/{doc_slug}.svg")
async def generate_svg_sparkline(user_slug: str, doc_slug: str):
    """
    if our Redis has its time-series module enabled, then show a sparkline of
    recent access.
    """
    points = data.timeSeries_dailyCount(user_slug, doc_slug, "read")
    return Response(content=svg_sparkline(points), media_type="image/svg+xml")


@app.get("/download/{user_slug}/{doc_slug}.epub")
async def generate_epub(user_slug, doc_slug):
    """
    Generates, caches and downloads an .epub; use a 'generating' notice to say
    reload the page in 5s; uses a simple redis lock or queue to show a 'reload
    in 5s' note.
    """

    file_name = "%s_%s.epub" % (user_slug, doc_slug)

    if data.epubCache_exists(user_slug, doc_slug):
        try:
            zip_data = data.epubCache_get(user_slug, doc_slug)
            zip_data_type = "application/epub+zip"
            zip_data_headers = {
                "Content-Disposition": f'inline; filename="{file_name}"'
            }
            return Response(
                content=zip_data, media_type=zip_data_type, headers=zip_data_headers
            )
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)
            data.epubCachePlaceholder_delete(user_slug, doc_slug)
            msg = "Temporary error generating ebook"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    elif data.epubCachePlaceholder_exists(user_slug, doc_slug):
        reload_html = views.get_template("reload.html").render(
            config=CONFIG, user_slug=user_slug, doc_slug=doc_slug, title="Generating..."
        )
        return HTMLResponse(content=reload_html, status_code=status.HTTP_202_ACCEPTED)

    else:
        # Generate and cache; requests for a lot of simultaneous
        # books that must all be generated could slow this down; add
        # a job queue later if that becomes necessary.

        data.epubCachePlaceholder_set(user_slug, doc_slug)  # with expiry

        file_path = os.path.join("/tmp", file_name)
        write_epub(user_slug, doc_slug, file_path)

        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
        else:
            logging.error("Download failed: " + file_path)
            msg = "Download failed"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

        data.epubCache_set(user_slug, doc_slug, content)
        data.epubCachePlaceholder_delete(user_slug, doc_slug)

        try:
            zip_data = data.epubCache_get(user_slug, doc_slug)
            zip_data_type = "application/epub+zip"
            zip_data_headers = {
                "Content-Disposition": f'inline; filename="{file_name}"'
            }
            return Response(
                content=zip_data, media_type=zip_data_type, headers=zip_data_headers
            )
        except Exception:
            data.epubCache_delete(user_slug, doc_slug)  # <-- Not right, rm
            msg = "Temporary error generating ebook"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)


COVER_DIMENSIONS = (1600, 2200)
MEDIA_DIMENSIONS = (1200, 630)

COLOR_TEXT = (248, 248, 248)  # <-- Alabaster
COLOR_SHADOW = (154, 174, 154)  # <-- Some greeny gray thing
COLOR_BACKGROUND = (160, 184, 160)  # <-- Norway, Summer Green, Pewter


def send_image(image: ImageType):
    """
    Download image without streaming it
    """
    image_bytes = io.BytesIO()
    image.save(image_bytes, "PNG", quality=85)
    return send_image_bytes(image_bytes.getvalue())


def send_image_bytes(image_bytes: bytes):
    """
    Download image without streaming it
    """
    return Response(image_bytes, media_type="image/png")


@app.get("/image/cover/{user_slug}/{doc_slug}.jpg")
def generate_cover(user_slug: str, doc_slug: str):
    image = cache_generate_cover(user_slug, doc_slug)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_cover(user_slug: str, doc_slug: str):
    metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
    if metadata:
        background = make_background(COVER_DIMENSIONS, COLOR_BACKGROUND)
        image = make_cover(
            background,
            [
                metadata["title"],
                metadata["summary"],
                metadata["author"],
                metadata["date"],
            ],
            [COLOR_TEXT, COLOR_SHADOW],
        )
        return image
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No metadata"
        )


@app.get("/image/card/{user_slug}/{doc_slug}.jpg")
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
            background,
            [
                metadata["title"],
                metadata["summary"],
            ],
            [COLOR_TEXT, COLOR_SHADOW],
            byline,
        )
        return image
    else:
        msg = "No metadata"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@app.get("/{user_slug}/{doc_slug}/image/quote/{checksum}/{encoded}.jpg")
def generate_quote(user_slug, doc_slug, checksum, encoded, request: Request):
    base_url = str(request.base_url)  # <-- URL type
    decoded = unquote_plus(encoded)
    image = cache_generate_quote(user_slug, doc_slug, checksum, decoded, base_url)
    return send_image(image)


@ttl_cache(ttl=3600)
def cache_generate_quote(user_slug, doc_slug, checksum, message, base_url):
    # TODO: Eliminate?
    key = bytes(CONFIG["APP_HASH"], "utf-8")
    message_bytes = bytes(message, "utf-8")
    required = hmac.new(key, message_bytes, "sha224").hexdigest()[:16]
    if checksum != required:
        msg = "No image"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    if data.userDocumentMetadata_exists(user_slug, doc_slug):
        metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
        shortcut = metadata.get("shortcut")
        if shortcut:
            base_url += "?" + shortcut
    quote_image = None
    if data.userDocumentImage_exists(user_slug, doc_slug, "quote.png"):
        image_data = data.userDocumentImage_get(user_slug, doc_slug, "quote.png")
        if image_data:
            width, height = IMAGE_DIMENSIONS["quote.png"]
            quote_image = Image.frombytes("RGB", (width, height), image_data)
    background_image_path = os.path.join(os.getcwd(), "resources/quote.png")
    background = Image.open(background_image_path).convert("RGB")
    byline = base_url
    image = make_quote(
        background,
        quote_image,
        [
            message,
        ],
        [COLOR_BACKGROUND, (238, 238, 238)],
        byline,
    )
    return image


# ----------------------------------------------------------
#                Special files; add sitemap?
# ----------------------------------------------------------


@app.get("/favicon.ico")
async def favicon_file():
    return FileResponse(path="static/favicon.ico", filename="favicon.ico")


@app.get("/robots.txt")
async def get_language_file():
    return FileResponse(path="static/robots.txt", filename="robots.txt")


app.mount("/dist", StaticFiles(directory="dist"), name="dist")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ----------------------------------------------------------
#                      Administrative
# ----------------------------------------------------------


@app.post("/admin/expire-cache")
def expire(
    login: LoginDependency,
):
    """
    Expire caches
    """
    login.require_admin()  # else 403

    data.userDocumentCache_deleteAll()
    data.epubCache_deleteAll()

    # 303 to forward POST to GET
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


# ----------------------------------------------------------
#                            Run
# ----------------------------------------------------------


def main():
    uvicorn.run("myapp:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
