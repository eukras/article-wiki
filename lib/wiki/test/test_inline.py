"""
Inline handles all inline markup. It is applied within Blocks.
"""

from .context import lib  # noqa: F401

from lib.wiki.inline import Inline, space_sentences


def test_brackets():
    test = Inline()
    assert '<strong>bold face</strong>' == test.brackets('*', "bold face")
    assert '<em><strong><u>bold-underline-italics</u></strong></em>' == \
        test.brackets('*_/', "bold-underline-italics")


def test_happy_path():
    test = Inline()
    out = '<strong>To boldly</strong> go where <u>none</u> have gone <em>before.</em>'
    assert out == test.process(
        "*[To boldly] go where _[none] have gone /[before.]"
    )
    out = '<ins>To boldly</ins> go where <del>none</del> ' + \
          'have gone <kbd>before</kbd>.'
    assert out == test.process(
        '+[To boldly] go where -[none] have gone `[before].'
    )
    out = '<sup>To boldly</sup> go where <sub>none</sub> ' + \
          'have gone before.'
    assert out == test.process(
        "'[To boldly] go where ,[none] have gone before."
    )


def test_typography():
    test = Inline()
    assert "x&mdash;x &ndash; x &copy; &trade;" == \
        test.typography("x --- x -- x (C) (TM)")
    assert "6&times;9 &hellip; 9&frac12; 9&frac14; 9&frac34;" == \
        test.typography("6x9 ... 9(1/2) 9(1/4) 9(3/4)")
    assert "“That’s ‘OK’,” I sez." == \
        test.typography("\"That's 'OK',\" I sez.")
    assert '&#8195;&#8195;&#8195;&#8195;' == \
        test.typography("(4EM)")


def test_space_sentence():
    assert space_sentences("\"S1.\" S2.") == "\"S1.\"&nbsp; S2."
    assert space_sentences("(S1.) S2.") == "(S1.)&nbsp; S2."
    assert space_sentences("(\"S1.\") S2.") == "(\"S1.\")&nbsp; S2."
    assert space_sentences('“Sentence 1.” (Sentence 2.) Sentence 3.') == \
        "“Sentence 1.”&nbsp; (Sentence 2.)&nbsp; Sentence 3."
    assert space_sentences('"Sentence 1." (Sentence 2.) Sentence 3.') == \
        "\"Sentence 1.\"&nbsp; (Sentence 2.)&nbsp; Sentence 3."
    assert space_sentences('(\'Sentence 1.\') ("Sentence 2.") Sentence 3.') == \
        "(\'Sentence 1.\')&nbsp; (\"Sentence 2.\")&nbsp; Sentence 3."


def test_apostrophes():
    test = Inline()
    assert '‘X’' == test.process("'X'")
    assert 'X’s' == test.process("X's")
    assert '(‘x)' == test.process("('x)")


def test_dashes():
    test = Inline()
    assert '0&ndash;9' == test.process("0-9")
    assert 'x &ndash; y' == test.process("x -- y")
    assert 'x&mdash;y' == test.process("x---y")
    assert '&ndash; x &ndash; y &ndash;' == test.process("-- x -- y --")
    assert '&ndash;x&ndash;y&ndash;' == test.process("--x--y--")
    assert '&mdash;x&mdash;y&mdash;' == test.process("--- x --- y ---")
    assert '&mdash;x&mdash;y&mdash;' == test.process("---x---y---")
