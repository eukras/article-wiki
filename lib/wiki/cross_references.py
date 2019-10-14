"""
Article Wiki.

Cross References placeholders.
"""

from html import escape

from slugify import slugify

from lib.wiki.geometry import get_words
from lib.wiki.outline import Outline
from lib.wiki.placeholders import Placeholders

class CrossReferences(object):
    """
    Manage internal links within a document.
    """

    def __init__(self, parts, outline):
        """
        Create contents list, replace cross-references with placeholders.
        """

        assert isinstance(parts, dict)
        assert all([isinstance(_, str) for _ in list(parts.keys())])
        assert all([isinstance(_, str) for _ in parts])
        assert isinstance(outline, Outline)

        self.regex = r'\@\[[^\]]+\][.,!?;:·]?'
        self.placeholders = Placeholders(self.regex, 'cr')
        self.outline = outline

    def insert(self, parts):
        """
        Use the placeholders object defined in init().
        """
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug=None):
        """
        Find first title that contains ALL terms.
        """
        terms = get_words(pattern)
        for (numbering, slug, title, title_slug, _) in self.outline:
            title_terms = get_words(title)
            # Require all given terms to match the title.
            # print set(terms), set(title_terms), set(terms) < set(title_terms)
            if set(terms) <= set(title_terms):
                section = ".".join(str(i) for i in numbering)
                slug = section + '_' + slug
                # leading '-' for short form
                if pattern[2] == '-':
                    fmt = "<a class=\"unmarked\" href=\"#%s\">&sect;%s</a>"
                    link = fmt % (slug, section)
                else:
                    fmt = "<a class=\"unmarked\" href=\"#%s\"><i>%s</i> (&sect;%s)</a>"
                    link = fmt % (slug, title.strip(), section)
                # trailing punctuation
                if pattern[-1] in ",.?!:;·":
                    link += pattern[-1]
                return link
        error = "<kbd class=\"wiki-error\">%s</kbd>"
        return error % escape(pattern)

    def replace(self, html_parts):
        """
        Replace each @[...] with a link to that section's #id.
        """
        return self.placeholders.replace(self.decorate, html_parts)
