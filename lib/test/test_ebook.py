"""
Test the redis interface for user and docs handling.
"""

import pytest
import os

from lib.data import Data, load_env_config
from lib.ebook import write_epub

config = load_env_config()
config['REDIS_DATABASE'] = 1
data = Data(config, strict=True)


@pytest.mark.integration
def test_write_epub():
    """
    Create a hash, find its key, delete it.
    """
    file_path = '/tmp/admin-help.epub'
    if os.path.exists(file_path):
        os.remove(file_path)

    write_epub('admin', 'help', file_path)
    assert os.path.exists(file_path)
