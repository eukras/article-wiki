"""
White Room Wiki: Verbatim

In White Room Wiki, verbatim text (nowiki, nomarkup) is indicated with double
curly brackets. e.g. {{ _underline_ }}, which will NOT be underlined.
"""

from html import escape

from lib.wiki.placeholders import Placeholders


class Verbatim(object):
    """
    Extract {{ verbatim }} blocks; restores as exact text entered; no markup.
    """

    def __init__(self):
        "This is a thin wrapper for Placeholders"
        regex = r"{{[^}]*}}"
        self.placeholders = Placeholders(regex, 'verbatim')

    def insert(self, parts):
        "Add placeholders."
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug=None):
        "Strip braces."
        trim_brackets = pattern[2:-2]
        return escape(trim_brackets)

    def replace(self, html_parts):
        "Replace verbatim text."
        return self.placeholders.replace(self.decorate, html_parts)
