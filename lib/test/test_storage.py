import pytest
import tempfile
import os

from .context import lib  # noqa: F401

from lib.storage import (
    compress_archive_dir,
    load_dir,
    make_zip_name,
    save_dir,
    write_archive_dir,
)

from lib.wiki.sample_data import minimal_document
from lib.wiki.utils import random_slug


@pytest.mark.integration
def test_save_dir_and_load_dir():
    """
    Save parts to a directory; load back; compare.

    Saving a changed dictionary should not retain obsolete parts on disk if
    delete_files is True.

    Automatically remove temporary directory afterward.
    """
    with tempfile.TemporaryDirectory() as dir_path:
        save_dir(dir_path, minimal_document)
        parts = load_dir(dir_path)
        assert parts == minimal_document
        # Now remove a part... (see sample_data)
        del parts["part-two"]
        save_dir(dir_path, parts, delete_files=True)
        parts2 = load_dir(dir_path)
        assert parts == parts2


@pytest.mark.integration
def test_user_archive():
    """
    Generate an archive file; check it exists.

    Automatically remove temporary directory afterward.
    """
    with tempfile.TemporaryDirectory() as dir_path:
        write_archive_dir(dir_path, minimal_document)
        user_slug = random_slug("test-user-")
        zip_name = make_zip_name(user_slug)
        zip_path = compress_archive_dir(dir_path, zip_name)
        assert os.path.exists(zip_path)
