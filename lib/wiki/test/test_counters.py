from .context import lib  # noqa: F401

from lib.wiki.counters import Letters, new_counter, Numbers, RomanNumerals, Symbols


def test_get_counter():
    ones = {
        "1": "1",
        "*": "*",
        "a": "a",
        "A": "A",
        "i": "i",
        "I": "I",
        "g": "α",
        "G": "Α",
    }  # <-- alpha
    for key, val in ones.items():
        counter = new_counter(key)
        assert next(counter) == val


def test_numbers():
    counter = Numbers()
    assert next(counter) == "1"
    assert next(counter) == "2"
    assert next(counter) == "3"
    counter = Numbers("9")
    assert next(counter) == "9"
    counter = Numbers("9")
    assert next(counter) == "9"
    assert next(counter) == "10"
    assert next(counter) == "11"


def test_roman_numerals():
    counter = RomanNumerals()
    assert next(counter) == "i"
    assert next(counter) == "ii"
    assert next(counter) == "iii"
    assert next(counter) == "iv"
    assert next(counter) == "v"
    counter = RomanNumerals("ix", True)  # <-- uppercase
    assert next(counter) == "IX"
    assert next(counter) == "X"
    assert next(counter) == "XI"
    counter = RomanNumerals("MMMMCMXCVIII", True)
    assert next(counter) == "MMMMCMXCVIII"
    assert next(counter) == "MMMMCMXCIX"
    assert next(counter) == "I"  # <-- clocked at 4999
    assert next(counter) == "II"


def test_letters():
    """
    LETTERS = u'abcdefjhijklmnopqrstuvwxyz'
    """
    counter = Letters()
    assert next(counter) == "a"
    assert next(counter) == "b"
    assert next(counter) == "c"
    counter = Letters("y")
    assert next(counter) == "y"
    assert next(counter) == "z"
    assert next(counter) == "aa"
    assert next(counter) == "ab"
    counter = Letters("ay", False)  # <-- lowercase
    assert next(counter) == "ay"
    assert next(counter) == "az"
    assert next(counter) == "ba"
    assert next(counter) == "bb"
    counter = Letters("zzy", True)  # <-- uppercase
    assert next(counter) == "ZZY"
    assert next(counter) == "ZZZ"
    assert next(counter) == "AAAA"
    assert next(counter) == "AAAB"


def test_symbols():
    """
    SYMBOLS = u'*†‡§‖¶'
    """
    counter = Symbols()
    assert next(counter) == "*"
    assert next(counter) == "†"
    assert next(counter) == "‡"
    counter = Symbols("‖")
    assert next(counter) == "‖"
    assert next(counter) == "¶"
    assert next(counter) == "**"
    assert next(counter) == "††"
    counter = Symbols("‖‖")
    assert next(counter) == "‖‖"
    assert next(counter) == "¶¶"
    assert next(counter) == "***"
    assert next(counter) == "†††"
