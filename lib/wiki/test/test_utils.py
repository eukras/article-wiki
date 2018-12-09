"""
The renderer handles HTML formatting; no need for other formats as yet.
"""

from .context import lib  # noqa: F401

from lib.wiki.utils import \
    compose, \
    html_escape, \
    pluralize, \
    split_options, \
    trim


def test_html_escape():
    """
    HTML-specific characters; quotes and apostrophes are handles by Inline().
    """
    mapping = [
        ("<", "&lt;"),
        (">", "&gt;"),
        # ("'", "&apos;"),
        # ('"', "&quot;"),
        ("&", "&amp;"),
    ]
    for (t1, t2) in mapping:
        assert t2 == html_escape(t1)


def test_pluralize():
    assert pluralize(1, 'tree') == '1 tree'
    assert pluralize(0, 'tree') == '0 trees'
    assert pluralize(2, 'tree') == '2 trees'
    assert pluralize(1, 'match', 'matches') == '1 match'
    assert pluralize(0, 'match', 'matches') == '0 matches'
    assert pluralize(2, 'match', 'matches') == '2 matches'


def test_split_options():
    assert split_options('()') == []
    assert split_options('(x)') == ['x']
    assert split_options('(x,y)') == ['x', 'y']
    assert split_options('(,)') == []
    assert split_options('') == []
    assert split_options('x, y 3') == ['x', 'y 3']


def test_trim():
    assert trim("\n   x\n   x\n") == 'x\nx'
    assert trim("\n   x\n    x\n") == 'x\n x'
    doc = """

        This is a test doc!

    """
    assert trim(doc) == 'This is a test doc!'


def test_compose():

    def add_a(x): return 'a' + x

    def add_b(x): return 'b' + x

    def add_c(x): return 'c' + x

    def add_d(x): return 'd' + x

    add = compose([add_a, add_b, add_c, add_d])
    assert add('e') == 'abcde'
