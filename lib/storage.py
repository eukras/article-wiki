"""
Disk storage functions for Article Wiki app.

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

from slugify import slugify


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
    for path in glob.glob(dir_path + '/*.txt'):
        name = path.replace(dir_path + '/', '').replace('.txt', '')
        slug = slugify(name)
        document[slug] = codecs.open(path, 'r', 'utf-8').read()
    return document


# -----------------
# Generate tarfiles
# -----------------

def make_tgz_name(user_slug: str) -> str:
    "Formats a timestamped archive name for this user_slug."
    name = "article-wiki_{:s}_{:d}-{:d}-{:d}.tgz"
    now = datetime.datetime.now()
    return name.format(user_slug, now.year, now.month, now.day)


def write_archive_dir(archive_data: Dict[str, Dict[str, str]], dir_path: str):
    """
    Writes user documents into a hiererchy of text files.

    For each {doc_slug: {part_slug: part_text}}, create
    """
    for doc_slug in archive_data:
        doc_dir = os.path.join(dir_path, doc_slug)
        if not os.path.isdir(doc_dir):
            os.makedirs(doc_dir)
        parts = archive_data[doc_slug]
        save_dir(doc_dir, parts)


def compress_archive_dir(dir_path: str, tgz_name: str) -> str:
    """
    For a directory dir_path create dir_path/tgz_name.

    Typically used `with tempfile.TemporaryDirectory()`, so permissions and
    cleanup are automatic. Archive file goes inside target dir, since this
    is a one-time operation on a unique temporary directory, and we know we
    have permissions for that directory.

    :param str dir_path: absolute path to target directory
    :param str tgz_name: name of archive file to create
    :return str: dir_path/tgz_name ... because why not?
    """
    cwd = os.getcwd()
    os.chdir(dir_path)
    command = "tar -czf {} */*.txt".format(tgz_name)
    process = subprocess.Popen(command, shell=True)
    process.communicate()  # <-- Wait for completion!
    os.chdir(cwd)
    tgz_path = os.path.join(dir_path, tgz_name)
    return tgz_path
