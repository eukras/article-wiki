import re

from lib.wiki.config import Config

class Shorthand(object):
    """
    Shorthand markup means using _underline_ instead of its bracket markup
    equivalent, _[underline].

    Examples of intebded usage: `teletype`, /italics/, *bold*, _underline_.

    Tuples to be given as [ [key, label], ... ]
    """

    def __init__(self, tuples=None):
        """
        Create a set of patterns that match e.g. "_an underline_" (for c ==
        '_'), and return "<u>an underline</u>" (for tag == 'u'), but doesn't
        cause_problems_with_snake_case. Likewise for 'an /italic/' that doesn't
        cause/problems/with/a/uri or a string like 'and/or either/or'.
        """
        use_tuples = tuples if tuples else Config.inline_shorthand_tuples
        self.regexes = []
        for key, label in use_tuples:
            self.add_pattern(key, label)

    def add_pattern(self, symbol, tag):
        """
        Python's problem is matching EITHER look-behind OR the start of the
        string, because Python's re library requires a fixed width pattern for
        look-behind. The same issue applies for look-ahead. There's a 'regex'
        lib in pip that doesn't have this limitation, but doesn't look as
        stable.

        The adopted solution is a set of three regexes that together handle
        the start and end of strings, plus the lookahead and lookbehind thatn
        prevents mismatching in the middle of strings.

        @todo: Consider a simpler solution using a single match for all four
        shorthand characters, and a \1 for back-matching.
        """
        delimiter = re.escape(symbol)
        regex_parts = [
            [r'^',             r'([^%s]+)' % delimiter, r'(?=[\W])'],
            [r'(?<=[\s\(\[])', r'([^%s]+)' % delimiter, r'(?=[\W])'],
            [r'(?<=[\s\(\[])', r'([^%s]+)' % delimiter, r'$'       ],
            [r'^',             r'([^%s]+)' % delimiter, r'$'       ],
        ]
        for lookbehind, match, lookahead in regex_parts:
            pattern = lookbehind + delimiter + match + delimiter + lookahead
            self.regexes.append([re.compile(pattern), tag])

    def replace(self, text):
        """
        Inefficient multi-pass regexes; but hey...
        """
        for regex, tag in self.regexes:
            text = re.sub(regex, r"<%s>\1</%s>" % (tag, tag), text)
        return text
