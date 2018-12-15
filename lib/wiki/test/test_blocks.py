"""
A BlockList is a parser that turns a text into a list of objects with a common
Block interface.
"""

from .context import lib  # noqa: F401

from lib.wiki.blocks import \
    BlockList, \
    CharacterBlock, \
    Divider, \
    FunctionBlock, \
    get_title_data, \
    list_block, \
    Paragraph, \
    start_of_block, \
    table_block

from lib.wiki.functions.base import Text
from lib.wiki.renderer import Html
from lib.wiki.settings import Settings
from lib.wiki.utils import trim


def test_start_of_block():
    "Advance the cursor to next non-whitespace start-of-line."
    text = trim("""
        01 3 5

        8


        12
        """)
    assert text[0] == '0'
    assert text[5] == '5'
    assert text[8] == '8'
    assert text[12:14] == '12'
    assert start_of_block(text, -1) == 0
    assert start_of_block(text, 0) == 0
    assert start_of_block(text, 4) == 8
    assert start_of_block(text, 5) == 8
    assert start_of_block(text, 8) == 8
    assert start_of_block(text, 9) == 12
    assert start_of_block(text, 12) == 12
    assert start_of_block(text, 13) == len(text) == 14
    assert start_of_block(text, 20) == len(text) == 14


def test_paragraph():
    block = Paragraph(trim("""
        x
        y
        x
        """))
    assert block.text() == 'x y x'
    assert block.html_only(Html(), Settings()) == '<p>x y x</p>'


def test_divider():
    block = Divider(trim("""
        - - -
        """))
    assert block.text() == '- - -'
    assert block.html_only(Html(), Settings()) == '<hr class="div-solid" />'


def test_character_block():
    block = CharacterBlock(trim("""
        + X
        """))
    assert block.text() == '\n+ X'  # <-- with leading space for a heading
    expected = '<h2 class="balance-text">X</h2>'
    assert block.html_only(Html(), Settings()) == expected


def test_function_block():
    block = FunctionBlock(Text, [], '-', 'x')
    assert block.text() == 'TEXT ---\nx\n---'
    assert block.html_only(Html(), Settings()) == '<pre>x</pre>'


def test_blocklist():
    "List of blocks..."
    # 1
    text = trim("""
        + Heading

        Paragraph

        - - -

        Paragraph

        TEXT (verse) ---
        Text
        ---

        Paragraph

        TEXT ---
        Text
        ---
        """)
    blocks = BlockList(text)
    class_list = [_.__class__.__name__ for _ in blocks]
    assert class_list == [
        'CharacterBlock',
        'Paragraph',
        'Divider',
        'Paragraph',
        'FunctionBlock',
        'Paragraph',
        'FunctionBlock',
    ]
    assert blocks.text() == "\n" + text
    # 2
    text = trim("""
        TEXT ---
        Text
        ---


        + Heading

        Paragraph

        - - -

        Paragraph

        TEXT (verse) ---
        Text
        ---

        Paragraph
        """)
    blocks = BlockList(text)
    class_list = [_.__class__.__name__ for _ in blocks]
    assert class_list == [
        'FunctionBlock',
        'CharacterBlock',
        'Paragraph',
        'Divider',
        'Paragraph',
        'FunctionBlock',
        'Paragraph',
    ]
    assert blocks.text() == text


def test_pop_titles():
    """
    We should be able to extract the title and summary lines.
    """
    text = trim("""
        Title

        = Summary

        Text
        """)
    blocks = BlockList(text)
    title, summary = blocks.pop_titles()
    assert title == "Title"
    assert summary == "Summary"
    assert blocks.text() == "Text"


def test_pop_titles_minimal():
    """
    We should be able to extract the title and summary lines.
    """
    text = trim("""
        Title

        = Summary
        """)
    blocks = BlockList(text)
    title, summary = blocks.pop_titles()
    assert title == "Title"
    assert summary == "Summary"
    assert blocks.text() == ""


def test_pop_titles_oneline():
    """
    We should be able to extract the title and summary lines.
    """
    text = trim("""
        Title
        """)
    blocks = BlockList(text)
    title, summary = blocks.pop_titles()
    assert title == "Title"
    assert summary == ""
    assert blocks.text() == ""


def test_get_title_data():
    """
    Index.txt should identify a sensible title (or 'Untitled'). A caption after
    the title is the summary.
    """
    index = trim("""
        This is the TITLE!

        = This is the SUMMARY!

        $ SLUG = This is the SLUG!

        This is the text.

        This is the text.

        This is the text.
        """)
    slug, title, title_slug, summary = get_title_data(index, 'index')
    assert slug == 'index'
    assert title == 'This is the TITLE!'
    assert title_slug == 'this-is-the-slug'
    assert summary == 'This is the SUMMARY!'


def test_empty_function_block():
    spaced = trim("""
        COMPACT ---

        ---
        """)
    unspaced = trim("""
        COMPACT ---
        ---
        """)
    blocks = BlockList(spaced)
    assert blocks.text() == unspaced
    blocks = BlockList(unspaced)
    assert blocks.text() == unspaced


def test_empty_blocklist():
    "Test function block with zero lines"
    text = trim("""
        TEXT ---
        Hi!
        ---
        """)
    blocks = BlockList(text)
    class_list = [_.__class__.__name__ for _ in blocks]
    assert class_list == ['FunctionBlock']
    assert blocks.text() == text


def test_nested_blocklist():
    "Test function block with zero lines"
    text = trim("""
        LEFT (35%) ---
        TEXT ===
        Hi!
        ===
        ---
        """)
    blocks = BlockList(text)
    class_list = [_.__class__.__name__ for _ in blocks]
    assert class_list == ['FunctionBlock']
    class_list = [_.__class__.__name__ for _ in list(iter(blocks))[0].blocks]
    assert class_list == ['FunctionBlock']
    assert blocks.text() == text


def test_list_block():
    "Test function block with zero lines"
    text = trim("""
        # Test 1
        # Test 2
        """)
    expect = trim("""
        <ol>
        <li>Test 1</li>
        <li>Test 2</li>
        </ol>
        """)
    actual = list_block(text, Settings())
    assert expect == actual


def test_list_block_recursor():
    "Test function block with zero lines"
    text = trim("""
        # Test 1
        # # Test 2
        """)
    expect = trim("""
        <ol>
        <li>Test 1</li>
        <ol>
        <li>Test 2</li>
        </ol>
        </ol>
        """)
    actual = list_block(text, Settings())
    assert expect == actual


def test_table_block():
    "Simple table, with headers"
    text = trim("""
        | Test 1 | Test 2
        | Test 3 | Test 4
        """)
    expect = trim("""
        <table class="table table-condensed">
        <tbody>
        <tr>
        <td class="text-left">Test 1</td>
        <td class="text-left">Test 2</td>
        </tr>
        <tr>
        <td class="text-left">Test 3</td>
        <td class="text-left">Test 4</td>
        </tr>
        </tbody>
        </table>
        """)
    actual = table_block(text, Settings())
    assert expect == actual
