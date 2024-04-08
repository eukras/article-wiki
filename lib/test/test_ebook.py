"""
Test writing epubs
"""

import os

import pytest

from lib.ebook import write_epub


@pytest.mark.integration
def test_write_epub():
    """
    Test writing epub to file
    """
    file_path = "/tmp/admin-help.epub"
    if os.path.exists(file_path):
        os.remove(file_path)

    write_epub("admin", "help", file_path)
    assert os.path.exists(file_path)
