"""
Test the redis interface for user and docs handling.
"""

from PIL import ImageFont

from .context import lib  # noqa: F401

from lib.linewrap import \
    line_width, \
    simple_wrap, \
    options, \
    raggedness, \
    best_wrap

FONT = ImageFont.load_default()  # <-- 6 x 11 pixel font <-- IMPORTANT

WORDS_114 = ['4444', '4444', '4444', '4444']
SPLIT_54 = [['4444', '4444'], ['4444', '4444']]


def test_default_font():
    x, y = FONT.getsize('4444')
    assert x == 24
    assert y == 11
    x, y = FONT.getsize('4444 4444')
    assert x == 54
    x, y = FONT.getsize('4444 4444 4444')
    assert x == 84
    x, y = FONT.getsize('4444 4444 4444 4444')
    assert x == 114


def test_line_width():
    assert line_width(FONT, WORDS_114) == 114


def test_simple_wrap():
    assert simple_wrap(FONT, WORDS_114, max_width_px=90) == [
        ['4444', '4444', '4444'],
        ['4444'],
    ]


def test_options():
    assert list(options(FONT, WORDS_114, max_width_px=100)) == [
        [['4444', '4444', '4444'], ['4444']],
        [['4444', '4444'], ['4444', '4444']],
    ]


def test_raggedness():
    assert raggedness(FONT, SPLIT_54, max_width_px=60) == 36 + 36


def test_best_wrap():
    assert best_wrap(FONT, WORDS_114, max_width_px=60) == [
        ['4444', '4444'],
        ['4444', '4444'],
    ]
