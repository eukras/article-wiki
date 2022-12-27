import datetime
import re

from typing import Union

from lib.data import Data
from lib.wiki.blocks import get_title_data
from lib.wiki.outline import iterate_parts
from lib.wiki.settings import Settings
from lib.wiki.wiki import Wiki


class Document(object):
    """
    Work with full wiki documents.

    - Keep the caching and metadata in sync behind the scenes.
    - Keep the app.py fairly thin.

    Usage:

    >>> data = Data(config)  # <-- redis connection

    >>> doc = Document(data)
    >>> doc.set_parts(host, user_slug, doc_slug, parts_dict)
    >>> doc.save()

    >>> doc.load(user_slug, doc_slug)  # <-- from database
    >>> doc.delete_part(part_slug)
    >>> doc.save()

    >>> file_name, file_text = doc.export_txt_file(user_slug, doc_slug)
    >>> doc.import_txt_file(txt_file)
    """

    def __init__(self, data: Data):
        """Specifies Redis connection to use."""
        self.host = None
        self.user_slug = None
        self.doc_slug = None
        self.parts = {}
        self.data = data

    def __repr__(self):
        """
        Returns a string representation.
        """
        return "{:s}:{:s} ({:d} part{:s})".format(
            self.user_slug,
            self.doc_slug,
            len(self.parts),
            '' if len(self.parts) == 1 else 's'
        )

    def __eq__(self, other):
        """
        Simple comparison of properties.
        """
        return self.parts == other.parts

    def protected_doc_slugs(self):
        """
        Admin pages are defined by doc_slugs that are never to be renamed by
        editing; or added to the Latest Changes list.
        """
        return ['fixtures', 'templates']

    def protected_part_slugs(self):
        """
        Part slugs that are never to be renamed by editing.
        """
        return ['index', 'biblio']

    def set_host(self, host: str):
        """
        Set domain name for FQDN link generation.
        """
        self.host = host

    def set_slugs(self, user_slug: str, doc_slug: str):
        """
        Sets or update the document identifiers. Saves a line, why not...
        """
        self.user_slug = user_slug
        self.doc_slug = doc_slug

    def require_slugs(self):
        """
        Dies if user_slug or doc_slug are not set.
        """
        ok_slugs = all([isinstance(self.user_slug, str),
                        isinstance(self.doc_slug, str)])
        if not ok_slugs:
            raise RuntimeError("Required: user_slug and doc_slug")

    def set_parts(self, user_slug: str, doc_slug: str, parts: dict):
        """
        Create from a dictionary {part_slug: part_text}.
        """
        self.user_slug = user_slug
        self.doc_slug = doc_slug
        self.parts = parts

    def require_parts(self):
        """
        Dies if self.parts is empty.
        """
        if len(self.parts) == 0:
            raise RuntimeError("Required: self.parts must not be empty")

    def load(self, user_slug: str, doc_slug: str) -> bool:
        """
        Gets a document from the database.

        Returns:
            Whether load was successful.
        """
        parts = self.data.userDocument_get(user_slug, doc_slug)
        if not isinstance(parts, dict):
            return False
        self.set_parts(user_slug, doc_slug, parts)
        return len(self.parts) > 0

    def save(self, pregenerate=True, update_doc_slug=None):
        """
        Stores self.parts; compare with self.old to know how to update the
        metadata and cache.
        """
        self.require_slugs()
        self.require_parts()

        # Old and new doc slugs may differ
        old_doc_slug = self.doc_slug
        new_doc_slug = self.doc_slug

        if update_doc_slug is None:
            update_doc_slug = all([
                # fixtures, templates
                old_doc_slug not in self.protected_doc_slugs(),
            ])

        if update_doc_slug:
            if 'index' in self.parts:
                new_text = self.parts['index']
                _, _, title_slug, _ = get_title_data(new_text, 'index')
                if self.doc_slug != title_slug:
                    new_doc_slug = title_slug

        with self.data as _:
            _.userDocument_set(self.user_slug, new_doc_slug, self.parts)
            if old_doc_slug not in self.protected_doc_slugs():
                _.userDocumentLastChanged_set(self.user_slug,
                                              old_doc_slug, new_doc_slug)
            _.userDocumentCache_delete(self.user_slug, old_doc_slug)
            _.userDocumentMetadata_delete(self.user_slug, old_doc_slug)

        self.doc_slug = new_doc_slug

        if pregenerate:

            wiki = Wiki(Settings({
                'config:host': self.host,  # <-- ebooks req. FQDN
                'config:user': self.user_slug,
                'config:document': self.doc_slug
            }))
            html = wiki.process(self.user_slug, self.doc_slug, self.parts)
            self.data.userDocumentCache_set(self.user_slug, self.doc_slug,
                                            html)

            metadata = wiki.compile_metadata(self.data.time_zone,
                                             self.user_slug, self.doc_slug)
            self.data.userDocumentMetadata_set(self.user_slug, self.doc_slug,
                                               metadata)

        return self.doc_slug

    def delete(self):
        """
        Drop whole document from database, including metadata, caching, etc.
        """
        with self.data as _:
            _.userDocumentCache_delete(self.user_slug, self.doc_slug)
            _.userDocumentLastChanged_delete(self.user_slug, self.doc_slug)
            _.userDocumentMetadata_delete(self.user_slug, self.doc_slug)
            _.userDocumentSet_delete(self.user_slug, self.doc_slug)
            _.userDocument_delete(self.user_slug, self.doc_slug)

    # ---------------------------------------------------------
    # Rename and delete functions also act on the TOC in index.
    # ---------------------------------------------------------

    def set_index(self, new_text: str) -> Union[str, None]:
        """
        Create or update the index part of an article. Return a suggested
        doc_slug based on the title that is not guaranteed to be unique. To
        ensure uniqueness use Data.unique_doc_slug().

        | edit/user/_/index   | creates new doc_slug and index part
        | edit/user/doc/index | edit index; may update doc_slug from title
        """
        _, title, title_slug, _ = get_title_data(new_text, 'index')
        self.doc_slug = title_slug
        self.parts['index'] = new_text
        return self.doc_slug

    def set_part(self, old_slug: str, new_text: str) -> Union[str, None]:
        """
        Replace a part; rename it if necessary; update contents in index.

        - part_slug may be '_' -> meaning generate a new one.
        - If a simple case, replace title line in the contents.

        | edit/user/doc/_     | creates new part_slug
        | edit/user/doc/part  | may update part_slug from title

        Args:
            old_slug: The part to replace
            new_text: The wiki text for this part.

        Returns:
            New part slug.
        """

        if old_slug in self.parts:
            _, old_title, _, _ = get_title_data(self.parts[old_slug], '')
        else:
            old_title = ""
        _, new_title, new_slug, _ = get_title_data(new_text, '')

        okay_to_rename = all([
            old_slug != new_slug,
            old_slug == '_' or old_slug in self.parts,
            old_slug not in self.protected_part_slugs(),
            new_slug not in self.parts
        ])
        if okay_to_rename:

            if old_slug in self.parts:
                del self.parts[old_slug]

            okay_to_update_index = all([
                'index' in self.parts,
                old_slug != 'index',
                new_slug != 'index'
            ])
            if okay_to_update_index:

                lines = []
                matched_yet = False

                for old_line in self.parts['index'].splitlines():

                    okay_to_replace_line = all([
                        not matched_yet,
                        old_line.startswith("- "),
                        old_line.endswith("- " + old_title)
                    ])
                    if okay_to_replace_line:
                        matched_yet = True
                        new_line = old_line.replace("- " + old_title,
                                                    "- " + new_title)
                        lines.append(new_line)
                    else:
                        lines.append(old_line)

                self.parts['index'] = "\n".join(lines)

        self.parts[new_slug] = new_text

        return new_slug if okay_to_rename else old_slug

    def delete_part(self, part_slug: str):
        """
        Remove a part. If unambiguous, delete title line in the contents.

        Just modify the new in-memory document; metadata changes are in save().

        Args:
            part_slug: The part to be deleted
        """
        if part_slug in self.parts:

            _, title, _, _ = get_title_data(self.parts[part_slug], part_slug)
            del self.parts[part_slug]

            okay_to_update_index = all([
                'index' in self.parts,
                part_slug != 'index'
            ])
            if okay_to_update_index:

                lines = []
                matched_yet = False

                for old_line in self.parts['index'].splitlines():

                    okay_to_delete_line = all([
                        not matched_yet,
                        old_line.startswith("- "),
                        old_line.endswith("- " + title)
                    ])
                    if okay_to_delete_line:
                        matched_yet = True
                    else:
                        lines.append(old_line)

                self.parts['index'] = "\n".join(lines)

    # -----------------------------------------------------------------
    # Join document into an export file, and split back into a document
    # -----------------------------------------------------------------

    def export_txt_file(self) -> (str, str):
        """
        Create a file name and file contents. This will usually be accessed
        through the web app.
        """

        def make_txt_name(user_slug: str, doc_slug: str) -> str:
            """Formats a timestamped file_name for a combined download file."""
            name = "article-wiki_{:s}_{:s}_{:04d}{:02d}{:02d}_{:02d}{:02d}.txt"
            now = datetime.datetime.now()
            return name.format(user_slug, doc_slug, now.year, now.month,
                               now.day, now.hour, now.minute)

        def make_txt_divider(number: str, part_slug: str) -> str:
            """Formats a numbered text divider for document exports."""
            divider = "\n\n\n\n..........  {:s} {:s}  ..........\n\n\n\n"
            return divider.format(number, part_slug)

        file_name = make_txt_name(self.user_slug, self.doc_slug)
        file_text = self.parts['index'] if 'index' in self.parts else ''
        outline_list = ['index']

        for (numbering, title, slug, text) in iterate_parts(self.parts):
            if slug != "index":
                number = ".".join([str(_) for _ in numbering])
                file_text += make_txt_divider(number, slug)
                file_text += text
                outline_list.append(slug)
        for slug in sorted(list(self.parts.keys())):
            if slug not in outline_list:
                file_text += make_txt_divider('_', slug)
                file_text += self.parts[slug]

        return file_name, file_text

    def import_txt_file(self, user_slug: str, doc_slug: str, file_text: str):
        """
        Takes an upload file and reconstructs its dictionary.

        The initial regex split will return a list of 3n + 1 elements:
        [
            index_text,
            part_num[1], part_name[1], part_text[1],
            part_num[2], part_name[2], part_text[2],
            ...
        ]
        """
        pattern = "\n\n\n\n.......... +(\\S+) (\\S+) +..........\n\n\n\n"
        matches = re.split(pattern, file_text)
        assert len(matches) % 3 == 1
        self.parts, pos = {}, 1
        self.parts['index'] = matches[0]
        while pos < len(matches):
            triple = matches[pos:pos + 3]
            if len(triple) == 3:
                _, part_slug, part_text = triple
                self.parts[part_slug] = part_text
            else:
                raise ValueError("Malformed import file.")
            pos += 3
        # If all OK...
        self.set_slugs(user_slug, doc_slug)
