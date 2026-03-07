import os
import tempfile
from lib.archive import user_document_zip_name, zip_name
from lib.storage import (
    compress_archive_dir,
    read_document_dir,
    uncompress_archive_dir,
    write_document_dir,
)
from lib.wiki.sample_data import minimal_document
from lib.wiki.utils import random_slug


def test_document_archive():
    """
    Generate an archive file; check it exists.

    Automatically remove temporary directory afterward.
    """
    with tempfile.TemporaryDirectory() as dir_path:
        write_document_dir(dir_path, minimal_document)
        user_slug = random_slug("test-user-")
        doc_slug = random_slug("test-doc-")
        zip_path = compress_archive_dir(
            dir_path, user_document_zip_name(user_slug, doc_slug)
        )
        assert os.path.exists(zip_path)
        uncompress_archive_dir(dir_path, zip_path)
        actual_document = read_document_dir(dir_path)
        assert actual_document == minimal_document
