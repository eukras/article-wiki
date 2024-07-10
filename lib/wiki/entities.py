"""
Article Wiki: Entities in HTML... allow direct usage in wiki.

Detect HTML Entities before wiki processing, remove them, and then put them
back afterward, as HTML.
"""

from lib.wiki.placeholders import Placeholders


class Entities(object):
    """
    Extract backslashes characters; restore with backslashes removed.
    """

    regex = r"\&\w+;"

    def __init__(self):
        "This is a thin wrapper for Placeholders"
        self.placeholders = Placeholders(self.regex, "en")

    def insert(self, parts):
        "Add placeholders."
        result = self.placeholders.insert(parts)
        return result

    def decorate(self, pattern, part_slug=None):
        """
        It's safe HTML, so insert it unchanged.
        """
        return pattern

    def replace(self, html_parts):
        "Replace backslashes characters."
        return self.placeholders.replace(self.decorate, html_parts)
