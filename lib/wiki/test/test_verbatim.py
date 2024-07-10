from .context import lib  # noqa: F401

from lib.wiki.placeholders import DELIMITER
from lib.wiki.verbatim import Verbatim
from lib.wiki.utils import trim


def test_verbatim():
    verbatim = Verbatim()
    parts = {
        "test": trim(
            """
        Grr. {{<blink>*[Arg!]</blink>}}. {{x2}}.
        """
        )
    }
    tokenized = verbatim.insert(parts)
    expected = {
        "test": trim(
            """
        Grr. %sverbatim:1%s. %sverbatim:2%s.
        """
        )
        % (DELIMITER, DELIMITER, DELIMITER, DELIMITER)
    }
    assert expected == tokenized
    decorated = verbatim.replace(tokenized)
    expected = {
        "test": trim(
            """
        Grr. &lt;blink&gt;*[Arg!]&lt;/blink&gt;. x2.
        """
        )
    }
    assert expected == decorated
