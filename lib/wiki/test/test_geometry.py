from .context import lib  # noqa: F401

from lib.wiki.geometry import get_words, split_to_array, split_to_dictionary
from lib.wiki.utils import trim


def test_get_words():
    "Note lowercase conversion."

    arg1 = "Here's the story!"
    out1 = ['heres', 'the', 'story']

    assert get_words(arg1) == out1

    arg2 = 'Ἐν ἀρχῇ ἦν ὁ λόγος'
    out2 = ['ἐν', 'ἀρχῇ', 'ἦν', 'ὁ', 'λόγος']

    assert get_words(arg2) == out2


def test_split_to_array():
    "Note one_line behaviour in split_to_array."
    arg = trim("""

        = x
        = y
        y
        = z

        """)
    out = [('=', 'x'), ('=', 'y y'), ('=', 'z')]
    assert split_to_array(arg, '=') == out

    arg = trim("""
        + Heading
        """)
    out = [('+', 'Heading')]
    assert split_to_array(arg, '.%#+') == out

    arg = trim("""

        . x
        . y
        .
        .
        . z

        """)
    out = [
        ('.', 'x'),
        ('.', 'y'),
        ('.', ''),
        ('.', ''),
        ('.', 'z')
    ]
    assert split_to_array(arg, '.') == out


def test_split_to_dictionary():

    arg = trim("""

        = x = 1
        = y = 2
        = z = 3

        """)
    out = {'x': '1', 'y': '2', 'z': '3'}

    assert split_to_dictionary(arg, '=') == out
