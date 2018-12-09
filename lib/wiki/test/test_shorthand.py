from .context import lib  # noqa: F401

from lib.wiki.shorthand import Shorthand


def test_underlines():
    _ = Shorthand()
    pairs = [
        ["simple _underline_ example", "simple <u>underline</u> example"],
        ["with _two words_ now", "with <u>two words</u> now"],
        ["Punctuation _test_.", "Punctuation <u>test</u>."],
        ["Punctuation _test._", "Punctuation <u>test.</u>"],
        ["A _test's_ apostrophe.", "A <u>test's</u> apostrophe."],
        ["dont_match_snake_case", "dont_match_snake_case"],
        ["_underline_ at start", "<u>underline</u> at start"],
        ["ends in _underline_", "ends in <u>underline</u>"],
        ["_start_ and _end_", "<u>start</u> and <u>end</u>"],
        ["(_brackets_)", "(<u>brackets</u>)"],
    ]
    for test, result in pairs:
        assert _.replace(test) == result


def test_mixed_tags():
    _ = Shorthand([
        ['/', 'i'],
        ['`', 'tt']
    ])
    pairs = [
        ["simple /italics/ example", "simple <i>italics</i> example"],
        ["test/check either/or", "test/check either/or"],
        ["http://example.org/some/path/", "http://example.org/some/path/"],
        ["http://example.org/some/path/", "http://example.org/some/path/"],
        ["http://localhost:8084/", "http://localhost:8084/"],
        ["simple `teletype` example", "simple <tt>teletype</tt> example"],
        ["simple `_teletype_` example", "simple <tt>_teletype_</tt> example"],
        ["(`brackets`)", "(<tt>brackets</tt>)"],
        ["`#brackets`", "<tt>#brackets</tt>"],
    ]
    for test, result in pairs:
        assert _.replace(test) == result
