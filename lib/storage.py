"""
Disk storage functions for Article Wiki app.

NOTE: To export to ZIP, use lib/archive, which works in-memory.

Article wiki need to read and write files when loading fixtures during
installation, creating tar files for download. In future this may include
version control operations.

- Save and load dictionaries as directories of .txt files: used for fixtures
  and in other disk-based operations.

- Turn a saved directory into a tarfile for http download.
"""

import codecs
import glob
import os
import shutil
import subprocess

from PIL.Image import Image
from PIL import Image as ImageClass

from lib.typing import DocumentParts, SiteUserDocuments, UserDocuments


# -------------------------
# Uilities for looping
# -------------------------


def require_dir(dir_path: str):
    if not os.path.isdir(dir_path):
        raise ValueError("No directory at {:s}".format(dir_path))


def list_dirs(dir_path: str) -> list[str]:
    file_pattern = os.path.join(dir_path, "*")
    return [
        os.path.basename(path)
        for path in glob.glob(file_pattern)
        if os.path.isdir(path)
    ]


def list_text_files(dir_path: str) -> list[str]:
    file_pattern = os.path.join(dir_path, "*.txt")
    return [
        os.path.basename(path)
        for path in glob.glob(file_pattern)
        if os.path.isfile(path)
    ]


def list_image_files(dir_path: str) -> list[str]:
    file_pattern = os.path.join(dir_path, "*.png")
    return [
        os.path.basename(path)
        for path in glob.glob(file_pattern)
        if os.path.isfile(path)
    ]


def clear_dir(dir_path):
    """
    Leaves the current directory empty of .txt, .png, and subdirs.
    """
    for dir_name in list_dirs(dir_path):
        doc_dir = os.path.join(dir_path, dir_name)
        shutil.rmtree(doc_dir)
    for file_name in list_text_files(dir_path) + list_image_files(dir_path):
        file_path = os.path.join(dir_path, file_name)
        os.remove(file_path)


# -----------------------
# Compress and uncompress
# -----------------------


def compress_archive_dir(dir_path: str, zip_name: str) -> str:
    """
    UNUSED: We create zipfiles in memory; see archive.py

    For a directory dir_path create dir_path/zip_name.

    Typically used `with tempfile.TemporaryDirectory()`, so permissions and
    cleanup are automatic. Archive file goes inside target dir, since this
    is a one-time operation on a unique temporary directory, and we know we
    have permissions for that directory.

    Args:
        dir_path: absolute path to target directory
        zip_name: name of archive file to create

    Returns:
        dir_path/zip_name
    """
    cwd = os.getcwd()
    os.chdir(dir_path)
    command = f"python -m zipfile -c {zip_name} */*"
    process = subprocess.Popen(command, shell=True)
    process.communicate()  # <-- Wait for completion!
    os.chdir(cwd)
    zip_path = os.path.join(dir_path, zip_name)
    print("ZIP_PATH", zip_path)
    return zip_path


def uncompress_archive_dir(dir_path: str, zip_name: str):
    cwd = os.getcwd()
    os.chdir(dir_path)
    command = f"python -m zipfile -e {zip_name} ."
    process = subprocess.Popen(command, shell=True)
    process.communicate()  # <-- Wait for completion!
    os.chdir(cwd)


# ----------------------------------------------
# Writing
# ----------------------------------------------


def write_site_dir(
    dir_path: str, site_user_documents: SiteUserDocuments, delete_files: bool = False
):
    if delete_files:
        clear_dir(dir_path)
    for user_slug in site_user_documents:
        user_dir = os.path.join(dir_path, user_slug)
        os.mkdir(user_dir)
        write_user_dir(user_dir, site_user_documents[user_slug])


def write_user_dir(dir_path: str, user_docs: UserDocuments, delete_files: bool = False):
    if delete_files:
        clear_dir(dir_path)
    for doc_slug in user_docs:
        doc_dir = os.path.join(dir_path, doc_slug)
        os.mkdir(doc_dir)
        write_document_dir(doc_dir, user_docs[doc_slug], delete_files)


def write_document_dir(
    dir_path: str,
    document: DocumentParts,
    delete_files: bool = False,
):
    """
    Save a dictionary to a directory as text files.

    Each {part_slug: part_text} pair should be written to disk as a
    part_slug.txt file containing text.

    Args:
        dir_path: absolute path to dir to write .txt files
        document: dictionary of {slug: text} pairs.
        delete_files: Whether to empty the dir before writing.
    """
    require_dir(dir_path)

    if delete_files:
        dir_files = os.path.join(dir_path, "*")
        for path in glob.glob(dir_files):
            os.remove(path)

    for key in document:
        if isinstance(document[key], str):
            path = os.path.join(dir_path, key + ".txt")
            write_text_file(path, document[key])
        elif key.endswith(".png") and isinstance(document[key], Image):
            path = os.path.join(dir_path, key)
            write_image_file(path, document[key])
        else:
            raise ValueError("Wiki files must be .txt or .png")


def write_text_file(path: str, text: str):
    print(f"- Writing {path}")
    # TODO: Switch to regular open() after 3.14
    fp = codecs.open(path, "w", "utf-8")
    fp.write(text)
    fp.close()


def write_image_file(path: str, image: Image):
    print(f"- Writing {path}")
    image.save(path)


# ------------------
# Read uploaded file
# ------------------


def read_site_dir(dir_path: str) -> SiteUserDocuments:
    """
    Hierarchy is site/user/document/part.txt
    """
    require_dir(dir_path)
    return {
        user_slug: read_user_dir(os.path.join(dir_path, user_slug))
        for user_slug in list_dirs(dir_path)
    }


def read_user_dir(dir_path: str) -> UserDocuments:
    require_dir(dir_path)
    return {
        doc_slug: read_document_dir(os.path.join(dir_path, doc_slug))
        for doc_slug in list_dirs(dir_path)
    }


def read_document_dir(dir_path: str) -> DocumentParts:
    """
    Reads user documents from a hierarchy of text files.

    For each {doc_slug: {part_slug: part_text}}, create
    """
    require_dir(dir_path)

    return {
        file_name.replace(".txt", ""): read_text_file(os.path.join(dir_path, file_name))
        for file_name in list_text_files(dir_path)
    } | {
        file_name: read_image_file(os.path.join(dir_path, file_name))
        for file_name in list_image_files(dir_path)
    }


def read_text_file(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


def read_image_file(file_path: str) -> Image:
    with ImageClass.open(file_path, "r") as image:
        image.load()  # <-- load image while file pointer exists
        return image


# def write_archive_dir(dir_path: str, archive_data: UserDocuments):
#     """
#     UNUSED. Downloads are generated in-memory by `wiki/archive.py`.
#
#     Writes user documents into a hierarchy of text files.
#
#     For each {doc_slug: {part_slug: part_text}}, create
#     """
#     for doc_slug in archive_data:
#         doc_dir = os.path.join(dir_path, doc_slug)
#         if not os.path.isdir(doc_dir):
#             os.makedirs(doc_dir)
#         parts = archive_data.get(doc_slug)
#         if isinstance(parts, dict):
#             save_dir(doc_dir, parts)
#         else:
#             print("Not a dict? " + doc_slug)
#
