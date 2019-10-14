from lxml import html

from .context import lib  # noqa: F401

from lib.wiki.index import Index
from lib.wiki.outline import Outline, default_counters
from lib.wiki.utils import trim


def test_get_count():
    parts = {
        'index': 'INDEX',
        'other': 'OTHER',
    }
    outline = Outline(parts, default_counters())
    index = Index(outline)
    assert index.get_count('index') == 'i'
    assert index.get_count('index') == 'ii'
    assert index.get_count('other') == 'i'
    assert index.get_count('other') == 'ii'


def test_tag():
    parts = {}
    outline = Outline(parts, default_counters())
    index = Index(outline)
    link = index.tag('alias', 'tag', 'subtag', '?', ['1', 'a'], 'i')

    assert '<a id="tag_subtag_1.a_i" href="#ref_tag_subtag_1.a_i">' in link
    assert 'alias?<sup>i</sup>' in link  # <-- (?)
    assert '</a>' in link

    back_link = '<a id="ref_tag_subtag_1.a_i" href="#tag_subtag_1.a_i">'
    assert back_link in index.tags['tag']['subtag']['1.a'][0]


def test_html_simplest():
    parts = {
        'index': trim("""
            My Document!

            It contains a #[Tag] and a %[Tag].

            ` Part One
        """),
        'part-one': trim("""
            Or an #[alias: Tag, subtag]?
        """),
    }
    outline = Outline(parts, default_counters())
    index = Index(outline)
    index.tags = {
        'tag': {
            'subtag': {
                '1.1': ['LINK']
            }
        }
    }
    out = index.html()
    dom = html.fragment_fromstring(out, create_parent='body')[0]
    assert len(dom.cssselect('div.indent-first-line')) == 1
    assert 'LINK' in out
