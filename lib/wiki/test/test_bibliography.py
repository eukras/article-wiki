from .context import lib  # noqa: F401

from lxml import html

from lib.wiki.bibliography import \
    Bibliography, \
    create_unique_labels, \
    get_sentences, \
    nonempty_lines, \
    split_label, \
    split_bibliography

from lib.wiki.outline import Outline, default_counters
from lib.wiki.utils import trim


def test_nonempty_lines():
    content = trim("""
        This is a test.

        This is a test.
        """)
    assert nonempty_lines(content) == ['This is a test.'] * 2


def test_get_sentences():
    arg = "RE: Hi. There? You!"
    out = ['RE:', 'Hi.', 'There?', 'You!']
    assert get_sentences(arg) == out


def test_split_bibliography():
    content = trim("""
        This is the body.
        """)
    assert split_bibliography(content) == (
        "This is the body.", None
    )
    content = trim("""
        This is the body.

        ___

        This is the bibliography.
        """)
    assert split_bibliography(content) == [
        "This is the body.", "This is the bibliography."
    ]


def test_split_label():
    line = "Author, etc."
    assert split_label(line) == ("Author, etc.", "")
    line = "Author, etc. Blah blah. 1999."
    assert split_label(line) == ("Author, etc.", "Blah blah. 1999.")
    line = "Author. 1999. Title. Publisher, City."
    assert split_label(line) == ("Author. 1999.", "Title. Publisher, City.")


def test_create_unique_labels():
    lines = [
        "Author. 1999. Title #1. Publisher, City.",
        "Author. 2000. Title #1. Publisher, City.",
        "Author. 2000. Title #2. Publisher, City.",
    ]
    assert create_unique_labels(lines) == {
        'Author. 1999.': "Title #1. Publisher, City.",
        'Author. 2000a.': "Title #1. Publisher, City.",
        'Author. 2000b.': "Title #2. Publisher, City.",
    }


def test_match():
    parts = {
        'biblio': trim("""
            Author. 1999. Title #1. Publisher, City.
            Author. 2000. Title #1. Publisher, City.
            Author. 2000. Title #2. Publisher, City.
            """),
    }
    outline = Outline(parts, default_counters())
    bibliography = Bibliography(parts, outline)
    assert bibliography.match('author') == "Author. 1999."
    assert bibliography.match('author 2000') == "Author. 2000a."


def test_get_count():
    parts = {
        'index': 'INDEX',
        'other': 'OTHER',
    }
    outline = Outline(parts, default_counters())
    bibliography = Bibliography(parts, outline)
    assert bibliography.get_count('index') == '*'
    assert bibliography.get_count('index') == '†'
    assert bibliography.get_count('index') == '‡'
    assert bibliography.get_count('other') == 'a'
    assert bibliography.get_count('other') == 'b'
    assert bibliography.get_count('other') == 'c'


def test_citation():
    parts = {}
    outline = Outline(parts, default_counters())
    bibliography = Bibliography(parts, outline)
    link = bibliography.citation(
        'Author /Title/', 'p.34', '.', 'Author. 2000.', ['1', 'a'], 3
    )

    assert '<a id="author-2000_1.a_3" href="#ref_author-2000_1.a_3">' in link
    assert '(Author <i>Title</i>, p.34).' in link  # <-- (?)
    assert '<sup>3</sup>' in link
    assert '</a>' in link

    back_link = '<a id="ref_author-2000_1.a_3" href="#author-2000_1.a_3">'
    assert back_link in bibliography.citations['Author. 2000.']['1.a'][0]


def test_html_simplest():
    parts = {
        'biblio': trim("""
            Author. 1999. Title #1. Publisher, City.
            Author. 2000. Title #1. Publisher, City.
            Author. 2000. Title #2. Publisher, City.
            """),
    }
    outline = Outline(parts, default_counters())
    bibliography = Bibliography(parts, outline)
    out = bibliography.html()
    dom = html.fragment_fromstring(out, create_parent='body')[0]
    assert len(dom.cssselect('div.indent-hanging')) == 3
