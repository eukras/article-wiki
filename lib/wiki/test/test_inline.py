"""
Inline handles all inline markup. It is applied within Blocks.
"""

from .context import lib  # noqa: F401

from lib.wiki.inline import Inline


def test_brackets():
    test = Inline()
    assert '<b>bold face</b>' == test.brackets('*', "bold face")
    assert '<b><u><i>bold-underline-italics</i></u></b>' == \
        test.brackets('*_/', "bold-underline-italics")


def test_inline():
    test = Inline()
    out = '<b>To boldly</b> go where <u>none</u> have gone <i>before.</i>'
    assert out == test.process(
        "*[To boldly] go where _[none] have gone /[before.]")

    out = '<ins>To boldly</ins> go where <del>none</del> ' + \
          'have gone <tt>before</tt>.'
    assert out == test.process(
        '+[To boldly] go where -[none] have gone `[before].')

    out = '<sup>To boldly</sup> go where <sub>none</sub> ' + \
          'have gone <kbd>before</kbd>.'
    assert out == test.process(
        "'[To boldly] go where ,[none] have gone ?[before].")


def test_typography():
    """
    General typographic features.
    """
    test = Inline()
    assert "x&mdash;x &ndash; x &rarr; x &larr; x &copy; &trade;" == \
        test.typography("x --- x -- x --> x <-- x (C) (TM)")
    assert "6&times;9 &hellip; 9&frac12; 9&frac14; 9&frac34;" == \
        test.typography("6x9 ... 9(1/2) 9(1/4) 9(3/4)")
    assert "★ ★★★½ ★★★★★ (6*)" == \
        test.typography("(*) (3.5*) (5*) (6*)")
    assert "&ldquo;That&rsquo;s &lsquo;OK&rsquo;,&rdquo; I sez." == \
        test.typography("\"That's 'OK',\" I sez.")
    assert '&#8195;&#8195;&#8195;&#8195;' == \
        test.typography("(4EM)")


def test_apostrophes():
    """
    Fiddly as usual.
    """
    test = Inline()
    assert '&lsquo;X&rsquo;' == \
        test.process("'X'")
    assert 'X&rsquo;s' == \
        test.process("X's")
    # assert '<b>X</b>&rsquo;s' == \
        # test.process("*[X]'s")
