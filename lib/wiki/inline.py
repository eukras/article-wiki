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
        '`': 'Teletype',
        '?': 'Keystrokes',
        '|': 'Marker (Black on White; Bold)',
        ';': 'Sans-Serif Font',
        '=': 'Small Caps',
        '!': 'Large text',
        '.': 'Small text',
        '+': 'Insertion',
        '-': 'Deletion',
        "'": 'Superscript',
        ',': 'Subscript',
        '}': 'Float Right',  # >
        '{': 'Float Left',  # <
    }

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
        Simple non-recursive parser to match *[...] patterns,
        but now with recursively combining characters.
        @todo: Recursion! (and/or combinations).
        """
        out = ''
        length = len(text)
        _ = 0
        while _ < length:
            match = self.pattern.search(text, _)
            if match is not None:
                start = match.start()
                if start > _:
                    out += self.typography(text[_:start])
                end = text.find(']', match.end()) + 1
                if end > 1:
                    part = text[start:end]  # '?[...]'
                    bracket = part.index('[')
                    control = part[0:bracket]
                    body = part[(bracket + 1):-1]
                    out += self.brackets(control, body)
                    _ = end
                else:
                    out += self.typography(text[_:])
                    _ = length
            else:
                out += self.typography(text[_:])
                _ = length
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
            (re.compile(r"--&gt;"), "&rarr;"),
            (re.compile(r"&lt;--"), "&larr;"),

            # en dash between numbers
            (re.compile(r"(?<=\d)-(?=\d)"), "&ndash;"),

            (re.compile(r"\s---\s"), "&mdash;"),
            (re.compile(r"\s--\s"), " &ndash; "),

            (re.compile(r"\(1\/2\)"), "&frac12;"),
            (re.compile(r"\(1\/4\)"), "&frac14;"),
            (re.compile(r"\(3\/4\)"), "&frac34;"),

            (re.compile(r"\.\.\."), "&hellip;"),
            (re.compile(r"(\d)x(\d)"), "\\1&times;\\2"),

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

            (re.compile(r"\(\*\)"), "★"),
            (re.compile(r"\(1\*\)"), "★"),
            (re.compile(r"\(1\.5\*\)"), "★" + "½"),
            (re.compile(r"\(2\*\)"), "★" * 2),
            (re.compile(r"\(2\.5\*\)"), "★" * 2 + "½"),
            (re.compile(r"\(3\*\)"), "★" * 3),
            (re.compile(r"\(3\.5\*\)"), "★" * 3 + "½"),
            (re.compile(r"\(4\*\)"), "★" * 4),
            (re.compile(r"\(4\.5\*\)"), "★" * 4 + "½"),
            (re.compile(r"\(5\*\)"), "★" * 5),

            (re.compile(r"\(EN\)"), "&#8194;"),
            (re.compile(r"\(2EN\)"), "&#8194;" * 2),
            (re.compile(r"\(4EN\)"), "&#8194;" * 4),

            (re.compile(r"\(EM\)"), "&#8195;"),
            (re.compile(r"\(2EM\)"), "&#8195;" * 2),
            (re.compile(r"\(4EM\)"), "&#8195;" * 4),

            # an apostrophe at the start may trail a ^[link], for example.
            (re.compile(r"^'s(\W)"), "&rsquo;s\\1"),

            (re.compile(r"(\S)'"), "\\1&rsquo;"),
            (re.compile(r"'(\S)"), "&lsquo;\\1"),
            (re.compile(r'(\S)"'), "\\1&rdquo;"),
            (re.compile(r'"(\S)'), "&ldquo;\\1"),

            (re.compile(r'\\' + '\n'), "<br/>\n"),

            (re.compile(r"(https?)://([\w%s]+)" % url_chars),
             '<a href="\\1://\\2">\\1://\\2</a>'),
            (re.compile(r"([\w\.\-\_]+)@([\w\.\-\_]+)"),
             '<a href="mailto:\\1@\\2">\\1@\\2</a>'),

            (re.compile(r"\(END\)"), "⬛")
        ]

    def brackets(self, char, content):
        """
        Process the *_[content] where char = '*_'.
        Prevent excessive recursion.
        """
        if len(char) == 0 or len(char) > 3:
            return content
        while len(char) > 1:
            # Recursion!
            char, content = char[:-1], self.brackets(char[-1], content)
        if char == '/':
            return '<i>%s</i>' % content
        elif char == '*':
            return '<b>%s</b>' % content
        elif char == '_':
            return '<u>%s</u>' % content
        elif char == '=':
            return '<span class="small-caps">%s</span>' % small_caps(content)
        elif char == '`':
            return '<tt>%s</tt>' % content
        elif char == '?':
            return '<kbd>%s</kbd>' % content
        elif char == ';':  # sans-serif
            return '<span class="opposite">%s</span>' % content
        elif char == '|':
            return '<var>%s</var>' % content
        # elif char == ';': # script
            # return '<span class="alternate">%s</span>' % content
        elif char == '!':
            return '<span class="large">%s</span>' % content
        elif char == '.':
            return '<small>%s</small>' % content
        elif char == "'":
            return '<sup>%s</sup>' % content
        elif char == ',':
            return '<sub>%s</sub>' % content
        elif char == '+':
            return '<ins>%s</ins>' % content
        elif char == '-':
            return '<del>%s</del>' % content
        elif char == '{':
            return '<span class="pull-left space-right">%s</span>' % content
        elif char == '}':
            return '<span class="pull-right space-left">%s</span>' % content
        elif char == '(':
            return '<span class="dropcap">%s</span>' % content
        else:
            return '<tt class="error">%s[%s]</tt>' % (html_escape(char),
                                                      html_escape(content))


# ----------------
# Module functions
# ----------------


def space_sentences(text: str) -> str:
    """
    Add an extra thin space after sentences; may not catch all cases.
    This is better done with NLTK, but would require rewriting the Inline
    module; using a clunky interim solution.
    """
    def repl(match) -> str:
        abbrevs = ['mr', 'st', 'mrs', 'ms', 'dr', 'jr', 'sr', 'sq'
                   'esp', 'inc', 'co', 'ltd', 'p.a', 'a.m', 'p.m',
                   'a.s.a.p', 'r.s.v.p', 'i.e', 'e.g', 'etc'
                   ]
        tail, punctuation, head = match.groups()
        if punctuation == '.' and tail.lower() in abbrevs:
            return tail + punctuation + " " + head
        else:
            return tail + punctuation + "&nbsp; " + head

    return re.sub(r'(\S+)([!?.][”’"\']?)\s+(\w)', repl, text)


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


def small_caps(content):
    """
    Wrap the capitals in <span> for better control of letter heights.
    """
    return re.sub('([A-Z]+)', '<span>\\1</span>', content)
