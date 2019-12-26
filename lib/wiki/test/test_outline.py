import pytest

from lxml import html
from re import findall

from .context import lib  # noqa: F401

from lib.wiki.outline import \
    Outline, \
    anchor_name, \
    create_outline, \
    default_counters, \
    enumerate_list, \
    extract_outline, \
    html_heading, \
    iterate_parts, \
    replace_title, \
    totalize

from lib.wiki.utils import trim


def test_anchor_name():
    with pytest.raises(AssertionError):
        assert anchor_name([], 'abc') == 'xx', "No numbering!"
    assert anchor_name(['1'], 'abc') == '1_abc'
    assert anchor_name(['1', '2', '3'], 'abc') == '1.2.3_abc'


def test_enumerate_list():
    arg = ['a', ['b', ['c', 'd']], 'e']
    out = [
        (['1'], 'a'),
        (['1', '1'], 'b'),
        (['1', '1', '1'], 'c'),
        (['1', '1', '2'], 'd'),
        (['2'], 'e')
    ]
    assert enumerate_list(arg, ['1', '1', '1', '1'], []) == out


def disable_test_create_outline():
    """
    @todo: create_outline should be able to detect single paragraphs.
    """
    arg = {'a': 'A', 'z': 'Z', 'c': 'C'}
    out = [
        (['1'], ('a', 'A', 'a', '')),
        (['2'], ('c', 'C', 'c', '')),
        (['3'], ('z', 'Z', 'z', ''))
    ]
    assert create_outline(arg) == out


def test_extract_outline():
    arg = trim("""
        Text

        - a
        - - b
        - - - c
        - d
        - e

        More text
        """)
    out = [
        (['1'], ('a', 'a', 'a', '')),
        (['1', 'a'], ('b', 'b', 'b', '')),
        (['1', 'a', 'i'], ('c', 'c', 'c', '')),
        (['2'], ('d', 'd', 'd', '')),
        (['3'], ('e', 'e', 'e', ''))
    ]
    assert extract_outline(arg, ['1', 'a', 'i']) == out


def test_html_heading():
    out = html_heading(
        ['1', '2', '3'], 'Title', 'title', '/edit/author/doc/'
    )
    dom = html.fragment_fromstring(out, create_parent='body')[0]
    assert len(dom.cssselect('div.pull-right a')) == 1


def test_outline():
    arg = {
        'index': trim("""
            Title

            - Chapter One
            - Chapter Two
            """),
        'chapter-one': "Chapter One\n\n" + ('word ' * 998)
    }
    outline = Outline(arg, default_counters())
    out = outline.html('/')  # <-- edit_base_uri
    # @todo: Check this.
    # dom = html.fragment_fromstring(out, create_parent='body')[0]
    # assert len(dom.cssselect('tr')) == 4
    rows = findall('<tr', out)
    assert len(rows) == 4


def test_find_numbering():
    arg = {
        'index': trim("""
            Title

            - Chapter One
            - - Chapter One Aye
            - Chapter Two
            """),
        'chapter-one': "Chapter One\n\n" + ('word ' * 998)
    }
    outline = Outline(arg, default_counters())
    assert outline.find_numbering('chapter-one') == ['1']
    assert outline.find_numbering('chapter-one-aye') == ['1', 'a']
    assert outline.find_numbering('chapter-two') == ['2']


def test_elements():
    arg = {
        'blog-1': "Blog One\n\n" + ('word ' * 500),
        'blog-2': "Blog Two\n\n" + ('word ' * 500)
    }
    outline = Outline(arg, default_counters())
    # Numbering, slug, title, title_slug, word count.
    expected = [(['1'], 'blog-1', 'Blog One', 'blog-one', 502),
                (['2'], 'blog-2', 'Blog Two', 'blog-two', 502)]
    assert outline.elements == expected


def test_iterate_parts():
    text = trim("""
            Chapter {}

            Text goes here.
            """)
    index = trim("""
            Title

            - Chapter One
            - - Chapter One Aye
            - Chapter Two
            """)
    arg = {
        'index': index,
        'chapter-one': text.format('One'),
        'chapter-one-aye': text.format('One Aye'),
        'chapter-two': text.format('Two')
    }
    gen = iterate_parts(arg)
    assert next(gen) == (['0'], 'Title', 'index', index)
    assert next(gen) == (['1'], 'Chapter One', 'chapter-one', text.format('One'))
    assert next(gen) == (['1', 'a'], 'Chapter One Aye', 'chapter-one-aye', text.format('One Aye'))
    assert next(gen) == (['2'], 'Chapter Two', 'chapter-two', text.format('Two'))


def test_totalise():
    before = [
        (['1'], 'one', 'One', 'one', 100),
        (['2'], 'two', 'Two', 'two', 100),
        (['2', 'a'], 'two-aye', 'Two-Aye', 'two-aye', 100),
        (['2', 'b'], 'two-bee', 'Two-Bee', 'two-bee', 100),
        (['3'], 'three', 'Three', 'three', 100)
    ]
    after = [
        (['1'], 'one', 'One', 'one', 100, 0),
        (['2'], 'two', 'Two', 'two', 100, 300),  # <-- NOTE
        (['2', 'a'], 'two-aye', 'Two-Aye', 'two-aye', 100, 0),
        (['2', 'b'], 'two-bee', 'Two-Bee', 'two-bee', 100, 0),
        (['3'], 'three', 'Three', 'three', 100, 0)
    ]
    assert totalize(before) == after


def test_replace_title():
    text = trim("""
        Index

        - Chapter One
        - - Chapter One Aye
        - Chapter Two
        """)
    expect = trim("""
        Index

        - The NEW Chapter One
        - - Chapter One Aye
        - Chapter Two
        """)
    assert expect == replace_title(text, "Chapter One", "The NEW Chapter One")
