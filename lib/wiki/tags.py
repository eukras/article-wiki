"""
White Room Wiki.

Citation placeholders replace ((Citations)) with links to the correct
bibliography element.
"""

import re

from lib.wiki.config import Config
from lib.wiki.placeholders import Placeholders
from lib.wiki.index import Index


class Tags(object):
    """
    Manage tags appearing in the index.
    """

    def __init__(self, index):
        """
        Create bibliography entries, and setup placeholder identifiers.
        """
        assert isinstance(index, Index)
        self.index = index

        regex = r'[#%%]\[[^\]]+\][%s]?' % re.escape(Config.punctuation)
        self.placeholders = Placeholders(regex, 'tag')

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
        numbering = self.index.outline.find_numbering(part_slug)
        alias, tag, subtag, punctuation = split_pattern(pattern)
        index = self.index.get_count(part_slug)
        return self.index.tag(
            alias, tag, subtag, punctuation, numbering, index
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
    Take #[alias:Tag, subtag],  # <-- and trailing punctuation
    Return alias, tag, subtag, and punctuation.
    """

    assert isinstance(pattern, str)

    if pattern[-1] in Config.punctuation:
        reference = pattern[2:-2]
        punctuation = pattern[-1]
    else:
        reference = pattern[2:-1]
        punctuation = ''

    alias = None

    clauses = reference.split(':') # <-- split once
    if len(clauses) > 1:
        alias, tags = ','.join(clauses[:-1]), clauses[-1]
    else:
        tags = reference

    # Split on ';' if any?

    clauses = tags.split(', ', 1)  # <-- only split once
    if len(clauses) > 1:
        tag, subtag = clauses
    else:
        tag, subtag = tags, ''

    if alias == None:
        alias = tag

    if pattern[0] == '#':  # <-- vs. '%', for case sensitivity
        tag = tag.lower()
        subtag = subtag.lower()

    return alias, tag, subtag, punctuation
