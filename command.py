"""
Command Line tool for Wiki admin.

save_user_document: Copy from Redis to install folders.
load_user_document: Copy from install folders to Redis.
"""

import sys

import click

from lib.data import CONFIG, Data, RedisTimer
from lib.ebook import write_epub
from lib.fixtures import load_fixtures, save_fixtures
from lib.html_document import HtmlDocument
from lib.views import make_views
from lib.wiki.settings import Settings
from lib.wiki.wiki import Wiki


def get_redis_client() -> Data:
    """
    Initialises a Redis client from environment variables.
    """
    if "pytest" in sys.modules:
        CONFIG["REDIS_DATABASE"] = "1"
    return Data(CONFIG)


# Redis, Jinja2
data = get_redis_client()
views = make_views()

# -------------------------------------------------------------------
#                               Commands
# -------------------------------------------------------------------


def generate_epub():
    """
    Writes an .epub to the /tmp dir.
    """
    file_path = "/tmp/eukras-how-should-christians-think-and-speak.epub"
    write_epub(CONFIG["ADMIN_USER"], "how-should-christians-think-and-speak", file_path)
    print("Generated ebook: {:s}".format(file_path))


def create_admin_user(data):
    """
    Creates an $ADMIN_USER with $ADMIN_USER_PASSWORD.
    """
    admin_user = {
        "slug": CONFIG["ADMIN_USER"],
        "password": CONFIG["ADMIN_USER_PASSWORD"],
        "is_admin": "YES",
    }
    data.user_set(CONFIG["ADMIN_USER"], admin_user)
    print("Created user: {:s}".format(CONFIG["ADMIN_USER"]))


def initialize():
    """
    Reset site to initial state.
    """
    data = get_redis_client()
    data.delete_site()
    create_admin_user(data)
    load_fixtures(data)
    refresh_site(CONFIG["HOST"])


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
    with RedisTimer(data, user_slug, doc_slug, "refresh"):
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


# -------------------------------------------------------------------
#                               Console
# -------------------------------------------------------------------


@click.command()
@click.argument("command")
def console(command):
    """Processes console commands."""
    if command == "show-config":
        for key, val in CONFIG.items():
            print(f"{key:>30}: {val}")
    elif command == "generate-epub":
        generate_epub()
    elif command == "initialize":
        initialize()
    elif command == "load-fixtures":
        load_fixtures(data)
        refresh_site(CONFIG["HOST"])
    elif command == "refresh-metadata":
        refresh_site(CONFIG["HOST"])
    elif command == "save-fixtures":
        save_fixtures(data)
    else:
        print("Commands:")
        print("  - show-config")
        print("  - generate-epub")
        print("  - initialize")
        print("  - load-fixtures")
        print("  - refresh-metadata")
        print("  - save-fixtures")


if __name__ == "__main__":
    console()
