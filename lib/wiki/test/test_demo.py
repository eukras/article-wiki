# Compare with wiki/tests/placeholders.py
#

from lxml import html

from .context import lib  # noqa: F401

from lib.wiki.placeholders import DELIMITER
from lib.wiki.settings import Settings
from lib.wiki.wiki import Demo
from lib.wiki.utils import trim


def test_basic_replacements():
    """
    @todo: There is an occassional thus-far-non-reproducable issue with DEMO
    blocks in the editor; they will sometimes wrap into e.g. ...

    DEMO === + Headline

    ... in cases like the one below. It's caused by the DEMO placeholders not
    matching their blocks, and the DEMO line being taken as the start of a
    paragraph and rewrapped accordingly.
    """
    settings = Settings()
    demo = Demo(settings)
    parts = {'test': trim("""
        Test

        DEMO ===
        TEST
        ===

        Test

        ~

        DEMO ===
        + Headline

        > Blockquote
        ===

        Test
        """)}
    tokenized = demo.insert(parts)
    expected = {'test': trim("""
        Test

        %sdemo:1%s

        Test

        ~

        %sdemo:2%s

        Test
        """) % (DELIMITER, DELIMITER, DELIMITER, DELIMITER)}
    assert expected == tokenized

    decorated = demo.replace(tokenized)
    __ = html.fromstring(decorated['test'])
    assert __.xpath("count(//div[@class='wiki-demo'])") == 2
    assert __.xpath("//pre[contains(., Test)]")
