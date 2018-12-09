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


def test_split_author():
    wiki = Wiki(Settings())
    expect = [['Name']]
    actual = wiki.split_author(trim("""
        Name
    """))
    assert expect == actual
    expect = [['Name', 'Email', 'Affiliation']]
    actual = wiki.split_author(trim("""
        Name / Email / Affiliation
    """))
    assert expect == actual
    expect = [
        ['Name', 'Email', 'Affiliation'],
        ['Name2', 'Email2', 'Affiliation2']
    ]
    actual = wiki.split_author(trim("""
        Name / Email / Affiliation
          + Name2 / Email2 / Affiliation2
    """))
    assert expect == actual


def test_process_simple():
    wiki = Wiki(Settings())
    document = {'sample': trim("""
        Title

        > Quote
        = Calvin, /Institutes/

        + Headline
        & Byline

        Paragraph

        * Bullets
        * Bullets
        """)}
    _ = wiki.process(document)
    __ = html.fromstring(str(_))
    assert __.xpath("//article/section")
    assert __.xpath("//h1/a[contains(., 'Title')]")
    assert __.xpath("//h2[contains(., 'Headline')]")
    assert __.xpath("//blockquote[contains(., 'Quote')]")
    assert __.xpath("//p[@class='caption'] and contains(., 'Calvin')")
    assert __.xpath("//p[@class='caption']/i[contains(., 'Institutes')]")
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

        ` Part One
        ` ` Part One Aye
        ` Part Two
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
