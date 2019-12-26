from lxml import html

from .context import lib  # noqa: F401

from lib.wiki.footnotes import Footnotes, split_pattern
from lib.wiki.links import Links
from lib.wiki.outline import Outline, default_counters
from lib.wiki.utils import trim

id_prefix ="PREFIX"


def test_split_pattern():
    assert split_pattern("^[Link]!") == ("Link", '!')
    assert split_pattern("^[Link]") == ("Link", '')


def sample_doc():
    """
    Basic document outline.
    """
    return {
        'index': trim("""
            My Document

            $ AUTHOR = Me!
            $ DATE = Now!

            This is my document.

            - Topic One
            - Topic Two
            - - Topic Two Subsection One.
            - Topic Three
            - Topic Four
            """),
        'topic-one': trim("""
            Topic One.

            This topic contains no footnotes.
            """),
        'topic-two': trim("""
            Topic Two.

            This topic contains a ^[footnote]!

            ^ The author, private conversation.
            """),
        'topic-two-subsection-one': trim("""
            Topic Two Subsection One.

            This topic contains a ^[link] as well as a
            ^[footnote]!

            ^ http://example.org
            ^ The author, private conversation.
            """),
        'topic-three': trim("""
            Topic Three

            This topic contains a ^[link] but not a
            ^[footnote]!

            ^ http://example.org
            """),
        'topic-four': trim("""
            Topic Four.

            This topic contains only a ^[footnote]!

            ^ http://example.org
            ^ The author, private conversation.
            """),
    }


def test_footnotes():
    """
    Simple count that we have the right number of footnotes.
    """
    parts = sample_doc()
    footnotes = Footnotes(parts, Outline(parts, default_counters()), id_prefix)
    links = Links(footnotes)
    new_parts = links.insert(parts)
    end_parts = links.replace(new_parts)
    out = footnotes.html()
    dom = html.fragment_fromstring(out, create_parent='body')[0]
    assert len(dom.cssselect('sup')) == 6
