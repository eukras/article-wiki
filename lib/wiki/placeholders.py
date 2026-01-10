"""
Article Wiki: Placeholders.
"""

import re
import collections


# High Voltage U+26a1; special marker.
# Will be stripped from any text in which it appears.
DELIMITER = "⚡"


class Placeholders(object):
    """
    Placeholders strip pattern matches out of documents (dictionaries of {slug:
    content}) and replace them with unique tokens, delimited by invisible ascii
    characters, which pass unmodified through wiki processing. When wiki
    processing is completed, the stored matches are formatted as HTML by a
    given decorator function and substituted back into the text, which by then
    is HTML. This is used in most of the wiki's special-purpose processing:

    * Demo blocks
    * Backslashed characters
    * No-Format blocks
    * MathJax blocks
    * Footnotes/Links
    * Indexes/Tags
    * Bibliographies
    * Outlines
    """

    def __init__(self, regex, marker, delimiter=DELIMITER):
        """
        Simple setup. Marker is a short string that uniquely distinguishes
        different placeholder types. If the delimiter were '|', and the marker
        were 'm', then the nth match in the source would be become '|m:n|'.
        In practice, an invisible, never-used chacacter is used as the
        delimiter, and any found in the source text should be preemptively
        stripped out by strip_delimiter_characters().
        """

        # Preconditions:
        assert len(marker) > 0
        assert isinstance(marker, str)
        assert re.search(r"^\w+$", marker)
        assert isinstance(delimiter, str)
        assert len(delimiter) == 1
        try:
            self.pattern_regex = re.compile(regex, re.MULTILINE | re.DOTALL)
        except re.error:
            assert False, "Invalid regex"

        self.delimiter = delimiter
        self.marker = marker
        self.placeholder_regex = re.compile(
            re.escape(self.delimiter)
            + re.escape(self.marker)
            + r":(\d+)"
            + re.escape(self.delimiter)
        )

        self.patterns = {}

    def __len__(self):
        """
        Return the number of placeholders held after insert().
        """
        return sum(len(self.patterns[_]) for _ in list(self.patterns.keys()))

    def get_placeholder(self, index):
        """
        Construct the placeholder text used to replace patterns in insert(),
        and then be replaced with HTML in replace().
        """
        assert isinstance(index, int)
        return "%s%s:%d%s" % (self.delimiter, self.marker, index, self.delimiter)

    def insert(self, parts):
        """
        Add placeholders to a list of input texts; these must occur in the same
        order as the list of texts used for output. It is up to the application
        to order these lists correctly (in the wiki this means the index first,
        then others following the order of the outline). A list of created
        containing the patterns in each text.  Output_parts must then be used
        on a list of HTML in the same order.
        """
        assert isinstance(parts, dict)
        assert all([isinstance(_, str) and isinstance(parts[_], str) for _ in parts])

        new_parts = {}
        self.patterns = {}

        for slug, text in parts.items():
            self.patterns[slug] = []
            cursor, counter = 0, 1
            new_text = ""

            matches = self.pattern_regex.finditer(text)
            for _ in matches:
                self.patterns[slug] += [text[_.start() : _.end()]]
                new_text += text[cursor : _.start()]
                new_text += (
                    self.delimiter + self.marker + ":" + str(counter) + self.delimiter
                )
                cursor = _.end()
                counter += 1
            new_text += text[cursor:]

            new_parts[slug] = new_text

        assert isinstance(new_parts, dict)
        assert all([isinstance(_, str) for _ in new_parts])
        assert isinstance(self.patterns, dict)
        assert all([isinstance(_, list) for _ in list(self.patterns.values())])

        return new_parts

    def replace(self, decorator, html_parts):
        """
        Replace placeholders with decorated text. A decorator is a string ->
        string function that takes the regexes matches from insert() and
        changes them into HTML. Normally the decorator function will be a method
        of the class using Placeholders. It is up to the application to order
        these html_parts the same as the wiki_parts. For a class like
        Footnotes, the ordre of these will be more important again, with the in
        the wiki this means the index first, then others following the order of
        the index's outline.
        """
        assert isinstance(decorator, collections.abc.Callable)
        assert isinstance(html_parts, dict)
        assert all([isinstance(_, str) for _ in html_parts])
        # if len(self.patterns) != len(html_parts):
        # print self.patterns.keys().sort()
        # print html_parts.keys().sort()

        new_html_parts = {}

        for slug, text in html_parts.items():
            matches = self.placeholder_regex.finditer(text)
            cursor, number = 0, 0
            new_html = ""
            zipper = list(zip(self.patterns[slug], matches))
            for pattern, match in zipper:
                # assert int(match.group(1)) == number  # <-- Sanity
                new_html += text[cursor : match.start()]
                new_html += decorator(pattern, slug)  # <-- Numbers lookup
                cursor = match.end()
                number += 1
            new_html += text[cursor:]
            new_html_parts[slug] = new_html

        return new_html_parts


def is_placeholder(text):
    """
    Identify if this text contains ONLY a placeholder.
    """
    pattern = r"^\s*%s\w+:\d+%s\s*$" % (re.escape(DELIMITER), re.escape(DELIMITER))
    return bool(re.match(pattern, text))


def strip_placeholder_delimiters(text):
    """
    At the start of processing, strip out any delimiter characters.
    """
    return text.replace(DELIMITER, "")
