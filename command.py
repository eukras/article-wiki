"""
Command Line tool for Wiki admin.

save_user_document: Copy from Redis to install folders.
load_user_document: Copy from install folders to Redis.
"""

import os
import sys

import click

from lib.data import Data, load_env_config
from lib.ebook import write_epub
from lib.document import Document
from lib.fixtures import load_fixtures, save_fixtures
from lib.storage import load_dir, save_dir


def get_redis_client() -> Data:
    """
    Initialises a Redis client from environment variables.
    """
    config = load_env_config()
    if "pytest" in sys.modules:
        config['REDIS_DATABASE'] = '1'
    return Data(config)


# -------------------------------------------------------------------
#                               Commands
# -------------------------------------------------------------------

def generate_epub():
    """
    Writes an .epub to the /tmp dir.
    """
    file_path = '/tmp/eukras-how-should-christians-think-and-speak.epub'
    write_epub('eukras', 'how-should-christians-think-and-speak', file_path)
    print("Generated ebook: {:s}".format(file_path))


def create_admin_user(data):
    """
    Creates an $ADMIN_USER with $ADMIN_USER_PASSWORD.
    """
    config = load_env_config()
    admin_user = {
        'slug': config['ADMIN_USER'],
        'password': config['ADMIN_USER_PASSWORD'],
        'is_admin': 'YES',
    }
    data.user_set(config['ADMIN_USER'], admin_user)
    print("Created user: {:s}".format(config['ADMIN_USER']))



def refresh_metadata():
    """
    Cycle through all documents for all users and regenerate their cache and
    metadata entries.
    """
    config = load_env_config()
    host = config['WEB_HOST'] + ':' + config['WEB_PORT']
    data = get_redis_client()
    for user_slug in data.userSet_list():
        for doc_slug in data.userDocumentSet_list(user_slug):
            document = Document(data)
            document.set_host(host)
            document.load(user_slug, doc_slug)
            document.save()


# -------------------------------------------------------------------
#                               Console
# -------------------------------------------------------------------

@click.command()
@click.argument('command')
@click.option('--title')
def console(command, title):
    """Processes console commands."""
    if command == 'generate-epub':
        generate_epub()
    elif command == 'initialize':
        data = get_redis_client()
        create_admin_user(data)
        load_fixtures(data)
    elif command == 'load-fixtures':
        data = get_redis_client()
        load_fixtures(data)
    elif command == 'refresh-metadata':
        refresh_metadata()
    elif command == 'save-fixtures':
        data = get_redis_client()
        save_fixtures(data)
    else:
        print("Commands:")
        print("  - generate-epub")
        print("  - initialize")
        print("  - load-fixtures")
        print("  - refresh-metadata")
        print("  - save-fixtures")


if __name__ == '__main__':
    console()
