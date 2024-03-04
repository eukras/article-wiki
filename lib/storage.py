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
import datetime
import glob
import os
import subprocess

from typing import Dict

from lib.slugs import slug


# -------------------------
# Load and Save Directories
# -------------------------

def save_dir(dir_path: str, document: dict, delete_files: bool = False):
    """
    Save a dictionary to a directory as text files.

    Each {part_slug: part_text} pair should be written to disk as a
    part_slug.txt file containing text.

    Args:
        dir_path: absolute path to dir to write .txt files
        document: dictionary of {slug: text} pairs.
        delete_files: Whether to empty the dir before writing.
    """
    if not os.path.isdir(dir_path):
        raise ValueError("No directory at {:s}".format(dir_path))
    if delete_files:
        txt_files = os.path.join(dir_path, "*.txt")
        for path in glob.glob(txt_files):
            os.remove(path)
    for key in document:
        target = os.path.join(dir_path, key + '.txt')
        fp = codecs.open(target, "w", "utf-8")
        fp.write(document[key])
        fp.close()


def load_dir(dir_path: str) -> dict:
    """
    Return .txt files in dir as dict of {basename: content}.

    Args:
        dir_path: absolute path to dir containing .txt files

    Returns:
        dictionary of {part_slug: text} pairs.
    """
    document = {}
    if not os.path.isdir(dir_path):
        raise ValueError("No directory at {:s}".format(dir_path))
    file_pattern = os.path.join(dir_path, '*.txt')
    file_paths = glob.glob(file_pattern)
    for path in file_paths:
        name = path.replace(dir_path + '/', '').replace('.txt', '')
        part_slug = slug(name)
        with open(path, 'r') as file:
            document[part_slug] = file.read()
        print("READ: {:s} ({:d})".format(part_slug, len(document[part_slug])))
    return document


# -----------------
# Generate zip file
# -----------------

def make_zip_name(user_slug: str) -> str:
    """
    Formats a timestamped archive name for this user_slug.
    """
    name = "article-wiki_{:s}_{:02d}{:02d}{:02d}_{:02}{:02d}.zip"
    now = datetime.datetime.now()
    return name.format(user_slug, now.year, now.month, now.day, now.hour,
                       now.minute)


def read_archive_dir(dir_path: str) -> Dict[str, Dict[str, str]]:
    """
    Writes user documents into a hierarchy of text files.

    For each {doc_slug: {part_slug: part_text}}, create
    """
    documentHash = {}
    if not os.path.isdir(dir_path):
        raise ValueError("No directory at {:s}".format(dir_path))
    file_pattern = os.path.join(dir_path, '*')
    for path in glob.glob(file_pattern):
        print('PATH', path)
        if os.path.isdir(path):
            name = os.path.basename(path).replace('.txt', '')
            part_slug = slug(name)
            documentHash[part_slug] = load_dir(path)
            print('len %d' % len(documentHash[part_slug]))
    return documentHash


def write_archive_dir(dir_path: str, archive_data: Dict[str, Dict[str, str]]):
    """
    Writes user documents into a hierarchy of text files.

    For each {doc_slug: {part_slug: part_text}}, create
    """
    for doc_slug in archive_data:
        doc_dir = os.path.join(dir_path, doc_slug)
        if not os.path.isdir(doc_dir):
            os.makedirs(doc_dir)
        parts = archive_data.get(doc_slug)
        if isinstance(parts, dict):
            save_dir(doc_dir, parts)
        else:
            print("Not a dict? " + doc_slug)


def compress_archive_dir(dir_path: str, zip_name: str) -> str:
    """
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
    print('ZIP_PATH', zip_path)
    return zip_path


def uncompress_archive_dir(dir_path: str, zip_name: str):
    """
    For a directory
    """
    cwd = os.getcwd()
    os.chdir(dir_path)
    # command = "unzip {:s}".format(zip_name)
    command = f"python -m zipfile -e {zip_name} ."
    process = subprocess.Popen(command, shell=True)
    process.communicate()  # <-- Wait for completion!
    os.chdir(cwd)
