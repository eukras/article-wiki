"""
Article Wiki.

Citation placeholders replace ((Citations)) with links to the correct
bibliography element.
"""

import re

from lib.slugs import slug
from lib.wiki.config import Config
from lib.wiki.placeholders import Placeholders
from lib.wiki.bibliography import Bibliography


class Citations(object):
    """
    Manage citations of the bibliography.
    """

    def __init__(self, bibliography):
        """
        Create bibliography entries, and setup placeholder identifiers.
        """
        assert isinstance(bibliography, Bibliography)
        self.bibliography = bibliography

        regex = r"~\[[^\)]+?\][%s]?" % re.escape(Config.punctuation)
        self.placeholders = Placeholders(regex, "citation")

        self.ibid = None  # <-- last bibliography label; @todo add opcit?
        self.counters = {}

    # ------------------------------------------------------------
    # Insert, decorate and replace make this work as a Placeholder
    # ------------------------------------------------------------

    def insert(self, parts):
        """
        Replace the bibliography brackets with markers, to exclude them from
        wiki processing.
        """
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug=None):
        """
        Format a bibliography bracket into a link to its bibliography entry.
        """
        numbering = self.bibliography.outline.find_numbering(part_slug)
        citation, note, punctuation = split_pattern(pattern)
        if self.ibid and slug(citation) == "ibid":
            index = self.bibliography.get_count(part_slug)
            return self.bibliography.citation(
                citation, note, punctuation, self.ibid, numbering, index
            )
        label = self.bibliography.match(citation)
        if label:
            self.ibid = label
            index = self.bibliography.get_count(part_slug)
            return self.bibliography.citation(
                citation, note, punctuation, label, numbering, index
            )
        else:
            self.ibid = None
            return self.bibliography.outline.error(
                part_slug, pattern, "Citation not matched in bibliography."
            )

    def replace(self, html_parts):
        """
        Replace the placeholders with HTML links.
        """
        return self.placeholders.replace(self.decorate, html_parts)


# ---------
# Utilities
# ---------


def split_pattern(pattern):
    """
    Take "~[Citation, Note].", and
    Return citation, note (if any) and punctuation (if any).
    """

    if pattern[-1] in Config.punctuation:
        reference = pattern[2:-2]
        punctuation = pattern[-1]
    else:
        reference = pattern[2:-1]
        punctuation = ""

    clauses = reference.split(",")  # <-- split once
    if len(clauses) > 1:
        citation, note = ",".join(clauses[:-1]), clauses[-1]
    else:
        citation, note = reference, ""

    return citation, note.strip(), punctuation
