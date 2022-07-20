"""
Test the redis interface for user and docs handling.
"""

import pytest
import os

from lib.data import Data
from lib.ebook import write_epub

config = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'REDIS_DATABASE': 1,  # <-- TESTING
    'ADMIN_USER': 'admin',
    'TIME_ZONE': 'Australia/Sydney',
}

data = Data(config, strict=True)


@pytest.mark.integration
def test_write_epub():
    """
    Create a hash, find its key, delete it.
    """

    file_path = '/tmp/eukras-help.epub'
    if os.path.exists(file_path):
        os.remove(file_path)

    write_epub('eukras', 'help', file_path)
    assert os.path.exists(file_path)
