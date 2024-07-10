"""
Placeholders match patterns in unicode dicts, replace them with markers that
have no significance for wiki markup, and later replace the markers with HTML
after wiki processing is done.

Placeholders are immplicitly tested in backslashes, citations, links, tags.
"""

from .context import lib  # noqa: F401

from lib.wiki.utils import trim
from lib.wiki.placeholders import is_placeholder, Placeholders


def test_backslashes():
    """
    Using backslash replacement for testing; there is an actual backslashes
    class that does this in the wiki.
    """
    parts = {
        "test": trim(
            r"""
        That\'s what it\'s about.
        """
        )
    }

    marker = "test"

    delimiter = "|"  # <-- For easy testing. This normally defaults to
    #     chr(30), an invisible 'record separator' in ASCII.

    def callback(x, _):
        return x[1:]  # <-- Remove leading slash from pattern;

    #     Ignore slug.

    backslashes = Placeholders(r"\\.", marker, delimiter)

    tokenized = backslashes.insert(parts)
    assert {"test": "That|test:1|s what it|test:2|s about."} == tokenized

    decorated = backslashes.replace(callback, tokenized)
    assert {"test": "That's what it's about."} == decorated


def test_is_placeholder():
    """
    Stripped text must contain ONLY a placeholder.
    """
    placeholder = Placeholders("a", "AAAA")
    text = " %s\n" % placeholder.get_placeholder(1)
    assert is_placeholder(text)
    assert not is_placeholder("! " + text)
