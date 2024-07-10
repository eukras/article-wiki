"""
Article Wiki: URLs

In Article Wiki, URLs are removed before processing so that they don't interact
strangely with surrounding text, trailing punctuation, or wiki formatting.

NOTE: Unused for now; would require changes to setting and footnote handling.
"""

import re

from html import escape
from validators.email import email

from lib.wiki.placeholders import Placeholders


class Urls(object):
    """
    Extract backslashes characters; restore with backslashes removed.
    """

    def __init__(self):
        "This is a thin wrapper for Placeholders"
        url_chars = re.escape(r".:\/_+?&=-#%~")
        regexps = [
            r"https?://[\w%s]+\w" % url_chars,  # <-- url
            r"[\w\.\-\_]+@[\w\.\-\_]+\w",  # <-- email
        ]
        regexp = "(" + "|".join(regexps) + ")"
        self.placeholders = Placeholders(regexp, "ur")

    def insert(self, parts):
        "Add placeholders."
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug=None):
        "HTML encode the URLs."
        if email(pattern):
            link = "mailto:%s" % pattern
        else:
            link = pattern
        html = '<a href="%s" target="_blank">%s</a>'
        return html % (link, escape(pattern))

    def replace(self, html_parts):
        "Put the URLs back in the finishes text"
        return self.placeholders.replace(self.decorate, html_parts)
