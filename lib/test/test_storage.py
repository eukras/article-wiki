import tempfile

from .context import lib  # noqa: F401

from lib.storage import (
    read_document_dir,
    read_site_dir,
    read_user_dir,
    write_document_dir,
    write_site_dir,
    write_user_dir,
)

from lib.wiki.sample_data import minimal_document


def test_read_and_write_document_dir():
    """
    Save archive to a directory; load back; compare; repeat with one file
    deleted. Automatically remove temporary directory afterward.
    """
    with tempfile.TemporaryDirectory() as dir_path:
        write_document_dir(dir_path, minimal_document)
        archive = read_document_dir(dir_path)
        assert archive == minimal_document
        # Now remove a part... (see sample_data)
        del archive["part-two"]
        write_document_dir(dir_path, archive, delete_files=True)
        archive2 = read_document_dir(dir_path)
        assert archive == archive2


def test_read_and_write_user_dir():
    """
    Save archive to a directory; load back; compare; repeat with one file
    deleted. Automatically remove temporary directory afterward.
    """
    doc_slug = "title"
    minimal_user_document = {doc_slug: minimal_document}
    with tempfile.TemporaryDirectory() as dir_path:
        write_user_dir(dir_path, minimal_user_document)
        archive = read_user_dir(dir_path)
        assert archive == minimal_user_document
        # Now remove a part... (see sample_data)
        del archive[doc_slug]["part-two"]
        write_user_dir(dir_path, archive, delete_files=True)
        archive2 = read_user_dir(dir_path)
        assert archive == archive2  # <-- recursive compare


def test_read_and_write_site_dir():
    """
    Save archive to a directory; load back; compare; repeat with one file
    deleted. Automatically remove temporary directory afterward.
    """
    user_slug, doc_slug = "user", "title"
    minimal_site_document = {user_slug: {doc_slug: minimal_document}}
    with tempfile.TemporaryDirectory() as dir_path:
        write_site_dir(dir_path, minimal_site_document)
        archive = read_site_dir(dir_path)
        assert archive == minimal_site_document
        # Now remove a part...
        del archive[user_slug][doc_slug]["part-two"]
        write_site_dir(dir_path, archive, delete_files=True)
        archive2 = read_site_dir(dir_path)
        assert archive == archive2  # <-- recursive compare
