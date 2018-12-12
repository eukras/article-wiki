"""
Article Wiki: Backslashes

In Article Wiki, backslashed characters are never processed by the wiki
formatting. They are replaced wih markers before wiki formatting happens, and
restored, without the backslashes, to the final HTML.
"""

from html import escape

from lib.wiki.placeholders import Placeholders


class Backslashes(object):
    """
    Extract backslashes characters; restore with backslashes removed.
    """

    def __init__(self):
        "This is a thin wrapper for Placeholders"
        self.placeholders = Placeholders(r'\\.', 'bs')

    def insert(self, parts):
        "Add placeholders."
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug=None):
        """
        Strip the leading slash, and HTML encode.
        This ensures that \< won't allow arbitrary script injection.
        """
        return escape(pattern[1:])

    def replace(self, html_parts):
        "Replace backslashes characters."
        return self.placeholders.replace(self.decorate, html_parts)
