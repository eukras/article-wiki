from .context import lib  # noqa: F401

from lib.wiki.footnotes import Footnotes, match_footnotes, match_links
from lib.wiki.outline import Outline, default_counters
from lib.wiki.utils import trim


def sample_doc():
    """
    Basic document outline.
    """
    return {
        "index": trim(
            """
            My Document

            $ AUTHOR = Me!
            $ DATE = Now!

            This is my document.

            ` Topic One
            ` Topic Two
            ` ` Topic Two Subsection One.
            ` Topic Three
            ` Topic Four
            """
        ),
        "topic-one": trim(
            """
            Topic One.

            This topic contains no footnotes.
            """
        ),
        "topic-two": trim(
            """
            Topic Two.

            This topic contains a ^[footnote]!

            ^ The author, private conversation.
            """
        ),
        "topic-two-subsection-one": trim(
            """
            Topic Two Subsection One.

            This topic contains a ^[link] as well as a
            ^[footnote]!

            ^ http://example.org
            ^ The author, private conversation.
            """
        ),
        "topic-three": trim(
            """
            Topic Three

            This topic contains a ^[link] but not a
            ^[footnote]!

            ^ http://example.org
            """
        ),
        "topic-four": trim(
            """
            Topic Four.

            This topic contains only a ^[footnote]!

            ^ http://example.org
            ^ The author, private conversation.
            """
        ),
    }


def test_match_links():
    parts = sample_doc()
    links = {_: match_links(text) for _, text in parts.items()}
    assert len(links["index"]) == 0
    assert len(links["topic-one"]) == 0
    assert len(links["topic-two"]) == 1
    assert len(links["topic-three"]) == 2
    assert len(links["topic-four"]) == 1
    assert links["topic-four"] == {
        "1": "^[footnote]!",
    }


def test_match_footnotes():
    parts = sample_doc()
    footnotes = {_: match_footnotes(text) for _, text in parts.items()}
    assert len(footnotes["index"]) == 0
    assert len(footnotes["topic-one"]) == 0
    assert len(footnotes["topic-two"]) == 1
    assert len(footnotes["topic-three"]) == 1
    assert len(footnotes["topic-four"]) == 2
    assert footnotes["topic-four"] == {
        "1": "http://example.org",
        "2": "The author, private conversation.",
    }


def test_constructor():
    parts = sample_doc()
    outline = Outline(parts, default_counters())
    footnotes = Footnotes(parts, outline, "prefix_")
    assert footnotes.outline.errors == {
        "topic-four": [("", "More <kbd>^[link]s</kbd> than footnotes! (+1)")],
        "topic-three": [("", "More footnotes than <kbd>^[link]s</kbd>! (+1)")],
    }
