"""
Inline wiki markup; typography and brackets.
"""

import re

from bleach import clean

from lib.wiki.icons import Icons
from lib.wiki.shorthand import Shorthand
from lib.wiki.utils import html_escape


class Inline(object):
    """
    Perform inline formatting using combinable bracket
    markers. This work with Typoraphy and Shorthand.
    """

    inline_format_characters = {
        '/': 'Italic',
        '*': 'Bold',
        '_': 'Underline',
        '=': 'Small Caps',
        '+': 'Insertion',
        '-': 'Deletion',
        '`': 'Teletype',
        '!': 'Marker',
        ';': 'Sans-Serif Font',
        "'": 'Superscript',
        ',': 'Subscript',
    }

    double_stops = [
        ('//', "<em>", "</em>"),
        ('**', "<b>", "</b>"),
        ('__', "<u>", "</u>"),
        ('==', "<span class=\"small-caps\">", "</span>"),
    ]

    def __init__(self):
        """
        Marshall several formatting classes.
        """
        chars = "".join(list(self.inline_format_characters.keys()))
        self.pattern = re.compile(
            "[%s]{1,5}\\[" % re.escape(chars)
        )
        self.shorthand = Shorthand()
        self.icons = Icons()

    def process(self, text: str) -> str:
        """
        Before any other inline formatting happens:

        - Double stops at the start of a block format it all.
        - Double stops in the middle will format the head and leave the tail
        unchanged.

        A bit of a hack with the special treatmennt for small_caps.

        ; ** Centered bold text
        . // Left-aligned italics
        . Bold lead text. ** Remainder of the block.
        > Small-caps lead text. == Remainder of the quote
        """
        for pattern, open_tag, close_tag in self.double_stops:
            if text.startswith(pattern + ' '):
                if pattern == '==':
                    return self.small_caps(text[3:])
                else:
                    return "".join([
                        open_tag,
                        self.process_after_splitting(text[3:]),
                        close_tag
                    ])
            elif ' ' + pattern + ' ' in text:
                parts = text.split(' ' + pattern + '', 1)
                if pattern == '==':
                    return self.small_caps(parts[0]) + "&nbsp; " + \
                        self.process_after_splitting(parts[1])
                else:
                    return "".join([
                        open_tag,
                        self.process_after_splitting(parts[0]),
                        close_tag + "&nbsp; ",
                        self.process_after_splitting(parts[1])
                    ])
        return self.process_after_splitting(text)

    def process_after_splitting(self, text: str) -> str:
        """
        Simple non-recursive parser to match *[...] patterns.
        """
        out = ''
        length = len(text)
        pos = 0
        while pos < length:
            match = self.pattern.search(text, pos)
            if match is not None:
                start = match.start()
                if start > pos:
                    out += self.typography(text[pos:start])
                end = text.find(']', match.end()) + 1
                if end > 1:
                    part = text[start:end]  # '?[...]'
                    bracket = part.index('[')
                    control = part[0:bracket]
                    body = part[(bracket + 1):-1]
                    out += self.brackets(control, body)
                    pos = end
                else:
                    out += self.typography(text[pos:])
                    pos = length
            else:
                out += self.typography(text[pos:])
                pos = length
        return out

    def typography(self, text: str) -> str:
        """
        Replace of all common typographical shortcuts, and add links. Add a
        tiny bit of extra space after sentences.

        Sentence handling has been removed here due to glitching.
        """
        _ = html_escape(text)
        for regex, replace in self.get_markup_tuples():
            _ = regex.sub(replace, _)
        _ = self.shorthand.replace(_)
        _ = self.icons.replace(_)
        _ = space_sentences(_)
        return _

    def get_markup_tuples(self):
        """
        All regular typography is done with a set of regex swaps.
        """
        url_chars = re.escape(r'.:\/_+?&=-#%~')
        return [
            # (re.compile(r"--&gt;"), "s⇐"),
            # (re.compile(r"&lt;--"), ""),

            # en dash between numbers
            (re.compile(r"(?<=\d)-(?=\d)"), "&ndash;"),
            (re.compile(r"(?<=\d)x(?=\d)"), "&times;"),

            (re.compile(r"(^|\s*)---($|\s*)"), "&mdash;"),
            (re.compile(r"(^|\s*)--($|\s*)"), "\\1&ndash;\\2"),

            (re.compile(r"\(1\/2\)"), "&frac12;"),
            (re.compile(r"\(1\/4\)"), "&frac14;"),
            (re.compile(r"\(3\/4\)"), "&frac34;"),

            (re.compile(r"\.\.\."), "&hellip;"),

            (re.compile(r"\(C\)"), "&copy;"),
            (re.compile(r"\(R\)"), "&reg;"),
            (re.compile(r"\(TM\)"), "&trade;"),
            (re.compile(r"\(D\)"), "&deg;"),

            # Some text-critical helpfulness
            (re.compile(r"\(PPY\)"), "𝔓"),
            (re.compile(r"\(MSS\)"), "𝔐"),

            (re.compile(r"\(S\)"), "&#8239;"),
            (re.compile(r"\(2S\)"), "&#8239;" * 2),
            (re.compile(r"\(4S\)"), "&#8239;" * 4),

            (re.compile(r"\(EN\)"), "&#8194;"),
            (re.compile(r"\(2EN\)"), "&#8194;" * 2),
            (re.compile(r"\(4EN\)"), "&#8194;" * 4),

            (re.compile(r"\(EM\)"), "&#8195;"),
            (re.compile(r"\(2EM\)"), "&#8195;" * 2),
            (re.compile(r"\(4EM\)"), "&#8195;" * 4),

            # an apostrophe at the start may trail a ^[link], for example.
            (re.compile(r"^'s(\W)"), "’\\1"),

            # Special case: a quote within a bracket ... handle square?
            (re.compile(r"\('(\S)"), "(‘\\1"),
            (re.compile(r'\("(\S)'), "(“\\1"),

            # ‘ ’ “ ”
            (re.compile(r"(\S)'"), "\\1’"),
            (re.compile(r"'(\S)"), "‘\\1"),
            (re.compile(r'(\S)"'), "\\1”"),
            (re.compile(r'"(\S)'), "“\\1"),

            (re.compile(r'\\' + '\n'), "<br/>\n"),

            # Web and email links
            (re.compile(r"(https?)://([\w%s]+)" % url_chars),
             '<a href="\\1://\\2">\\1://\\2</a>'),
            (re.compile(r"([\w\.\-\_]+)@([\w\.\-\_]+)"),
             '<a href="mailto:\\1@\\2">\\1@\\2</a>'),

            (re.compile(r"\(END\)"), "⬛")
        ]

    def brackets(self, char, content, depth=0):
        """
        Process the *_[content] where char = '*_'.
        Must use typography onc
        Prevent excessive recursion.
        """

        open_tags = []
        close_tags = []

        if '=' in char:
            content_html = self.small_caps(content)
        else:
            content_html = self.typography(content)

        if '/' in char:
            open_tags.append('<em>')
            close_tags.insert(0, '</em>')
        if '*' in char:
            open_tags.append('<strong>')
            close_tags.insert(0, '</strong>')
        if char == '=':
            pass  # <-- Already handled by small_caps()
        if '_' in char:
            open_tags.append('<u>')
            close_tags.insert(0, '</u>')
        if char == '+':
            open_tags.append('<ins>')
            close_tags.insert(0, '</ins>')
        if char == '-':
            open_tags.append('<del>')
            close_tags.insert(0, '</del>')

        if '`' in char:
            open_tags.append('<kbd>')
            close_tags.insert(0, '</kbd>')
        if ';' in char:
            open_tags.append('<span class="opposite">')
            close_tags.insert(0, '</span>')
        if '!' in char:
            open_tags.append('<var>')
            close_tags.insert(0, '</var>')
        if "'" in char:
            open_tags.append('<sup>')
            close_tags.insert(0, '</sup>')
        if ',' in char:
            open_tags.append('<sub>')
            close_tags.insert(0, '</sub>')

        return "".join(open_tags) + content_html + "".join(close_tags)

    def small_caps(self, content):
        """
        Wrap the capitals in <span> for better control of letter heights.
        """
        return '<span class="small-caps">' + \
            re.sub(
                '([A-Z]+)',
                '<span>\\1</span>',
                self.typography(content)
                ) + \
            '</span>'


# ----------------
# Module functions
# ----------------


def space_sentences(text: str) -> str:
    """
    Common abbreviations and acronyms can be handled with backslashing.
    Mainly we need to deal with end-of-sentence punctuation that is followed by
    other characters, like right-parentheses, quotes, or other punctuation.
    """

    def repl(match) -> str:
        tail, punctuation, head = match.groups()
        return tail + punctuation + "&nbsp; " + head

    return re.sub(r'(\S+)([!?.][”’"\'\)\]]{0,3})\s+(\S)', repl, text)


def strip_markup(content):
    """
    Convert to HTML and strip out tags.

    This is effective but inefficient.
    """
    inline = Inline()
    return clean(inline.process(content),
                 tags=[],
                 strip=True,
                 strip_comments=True)
