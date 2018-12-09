"""
White Room Wiki.

Citation placeholders replace ((Citations)) with links to the correct
bibliography element.
"""


from lib.wiki.placeholders import Placeholders
from lib.wiki.footnotes import Footnotes


class Links(object):
    """
    Manage tags appearing in the index.
    """

    def __init__(self, footnotes):
        """
        Create bibliography entries, and setup placeholder identifiers.
        """
        assert isinstance(footnotes, Footnotes)

        self.footnotes = footnotes

        regex = r'\^\[[^\]]+\][.,!?;:·]?'  # <-- see decorator
        self.placeholders = Placeholders(regex, 'link')

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
        index = self.footnotes.get_count(part_slug)
        return self.footnotes.footnote(pattern, part_slug, index)

    def replace(self, html_parts):
        """
        Replace the placeholders with HTML links.
        """
        return self.placeholders.replace(self.decorate, html_parts)
