from .context import lib  # noqa: F401

from lib.wiki.utils import trim
from lib.wiki.blocks import BlockList

from lib.wiki.functions.grid import Grid


def test_multirows():
    """
    Basic sanity check...
    """
    text = trim("""
        GRID +++
        Top Left
        ---
        Top Right
        ===
        Bottom Left
        ---
        Bottom Right
        +++
        """)
    blocks = BlockList(text)
    class_list = [_.__class__.__name__ for _ in blocks]
    assert class_list == [
        'FunctionBlock',
    ]
    block = blocks.blocks[0]
    assert block.function_class == Grid
    assert block.options == []
    assert block.content == trim("""
        Top Left
        ---
        Top Right
        ===
        Bottom Left
        ---
        Bottom Right
        """)
