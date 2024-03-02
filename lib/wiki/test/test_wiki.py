from lxml import html

from .context import lib  # noqa: F401

from lib.wiki.settings import Settings
from lib.wiki.utils import trim
from lib.wiki.wiki import \
    Wiki, \
    clean_document, \
    clean_text, \
    is_index_part, \
    reformat_part


def test_clean_document():
    document = {
        'index.txt': 'INDEX',
        'chapter.txt': 'CHAPTER',
        'image.jpg': 'IMAGE',
    }
    expect = ({
        'index': 'INDEX',
        'chapter': 'CHAPTER',
    }, [
        'image.jpg'
    ])
    actual = clean_document(document)
    assert expect == actual


def test_process_simple():
    wiki = Wiki(Settings())
    document = {'sample': trim("""
        Title

        > Quote
        = Calvin, /Institutes/

        @ Headline

        Paragraph

        * Bullets
        * Bullets
        """)}
    _ = wiki.process('user-slug', 'doc-slug', document)
    __ = html.fromstring(str(_))
    assert __.xpath("//h1[contains(., 'Title')]")
    assert __.xpath("//blockquote[contains(., 'Quote')]")
    assert __.xpath("//p[@class='caption'] and contains(., 'Calvin')")
    assert __.xpath("//p[@class='caption']/em[contains(., 'Institutes')]")
    assert __.xpath("//p[@class='subhead'][contains(., 'Headline')]")
    assert __.xpath("//p[contains(., 'Paragraph')]")
    assert __.xpath("count(//ul/li[contains(., 'Bullets')])") == 2


def test_is_index_page():
    page = trim("""
        Title

        OK
        """)
    assert not is_index_part(page)
    page = trim("""
        Title

        $ AUTHOR = Author Name

        OK
        """)
    assert is_index_part(page)
    page = trim("""
        Title

        OK

        - Part One
        - - Part One Aye
        - Part Two
        """)
    assert is_index_part(page)


def test_reformat_part():
    part = trim("""
        Some Title

        DEMO ===
        + Test Headline Wrapping

        Example text
        ===
        """)
    assert part == reformat_part('index', clean_text(part))
    part = trim("""
        DEMO ===
        + Test Headline Wrapping

        Example text
        ===
        """)
    assert part == reformat_part('random', clean_text(part))
