"""
Test the redis interface for user and docs handling.
"""

from PIL import ImageFont

from .context import lib  # noqa: F401

from lib.linewrap import line_width, simple_wrap, options, raggedness, best_wrap

FONT = ImageFont.load_default()  # <-- 6 x 11 pixel font <-- IMPORTANT

WORDS_114 = ["4444", "4444", "4444", "4444"]
SPLIT_54 = [["4444", "4444"], ["4444", "4444"]]


def test_default_font():
    x = FONT.getlength("4444")
    assert x == 24
    x = FONT.getlength("4444 4444")
    assert x == 50
    x = FONT.getlength("4444 4444 4444")
    assert x == 76
    x = FONT.getlength("4444 4444 4444 4444")
    assert x == 102


def test_line_width():
    assert line_width(FONT, WORDS_114) == 102


def test_simple_wrap():
    assert simple_wrap(FONT, WORDS_114, max_width_px=90) == [
        ["4444", "4444", "4444"],
        ["4444"],
    ]


def test_options():
    assert list(options(FONT, WORDS_114, max_width_px=100)) == [
        [["4444", "4444", "4444"], ["4444"]],
        [["4444", "4444"], ["4444", "4444"]],
    ]


def test_raggedness():
    assert raggedness(FONT, SPLIT_54, max_width_px=60) == 200


def test_best_wrap():
    assert best_wrap(FONT, WORDS_114, max_width_px=60) == [
        ["4444", "4444"],
        ["4444", "4444"],
    ]
