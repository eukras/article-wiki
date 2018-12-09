"""
Depends on:
wiki/tests/outline.py
wiki/tests/bibliography.py
"""

from lxml import html
from sortedcontainers import SortedDict

from .context import lib  # noqa: F401

from lib.wiki.bibliography import Bibliography
from lib.wiki.citations import Citations, split_pattern
from lib.wiki.outline import Outline, default_counters
from lib.wiki.placeholders import DELIMITER
from lib.wiki.utils import trim


def test_split_pattern():
    assert split_pattern("~[Smith]") == ("Smith", '', '')
    assert split_pattern("~[Smith, p.34].") == ("Smith", "p.34", ".")
    assert split_pattern("~[Smith, Title, p.34].") == ("Smith, Title", "p.34",
                                                       ".")


def test_constructor():
    parts = {
        'index': trim("""
            My Document!

            It contains a reference to ~[Chapman, /Conversation/, p.34].
        """),
        'biblio': trim("""
            Chapman, Nigel. 2014. Private conversation.
            Chapman, Nigel. 2014. Private conversation. #2.
        """),
    }

    outline = Outline(parts, default_counters())
    bibliography = Bibliography(parts, outline)
    citations = Citations(bibliography)

    assert bibliography.entries == SortedDict({
        "Chapman, Nigel. 2014a.": "Private conversation.",
        "Chapman, Nigel. 2014b.": "Private conversation. #2.",
        })

    new_parts = citations.insert(parts)

    assert new_parts == {
        'index': trim("""
            My Document!

            It contains a reference to %scitation:1%s
            """) % (DELIMITER, DELIMITER),       # ^ note the missing fullstop
        'biblio': trim("""
            Chapman, Nigel. 2014. Private conversation.
            Chapman, Nigel. 2014. Private conversation. #2.
            """),
        }

    end_parts = citations.replace(new_parts)
    assert '<i>Conversation</i>' in end_parts['index']
    assert 'p.34' in end_parts['index']
    dom = html.fragment_fromstring(end_parts['index'], create_parent='body')[0]
    assert len(dom.cssselect('a')) == 1
