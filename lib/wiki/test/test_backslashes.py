from .context import lib  # noqa: F401

from lib.wiki.backslashes import Backslashes
from lib.wiki.placeholders import DELIMITER


def test_backslashes():
    """
    Test that I can save and restore chars; HTML special chars should use HTML
    entities.
    """
    parts = {"test": r"\*bold\*"}
    _ = Backslashes()
    tokenized = _.insert(parts)
    expected = {"test": DELIMITER.join(["", "bs:1", "bold", "bs:2", ""])}
    assert expected == tokenized
    decorated = _.replace(tokenized)
    assert {"test": "*bold*"} == decorated


def test_backslashes_with_entities():
    """
    Test that I can save and restore chars; HTML special chars should use HTML
    entities.
    """
    parts = {"test": r"That\'s what it\'s about."}
    _ = Backslashes()
    tokenized = _.insert(parts)
    expected = {
        "test": DELIMITER.join(["That", "bs:1", "s what it", "bs:2", "s about."])
    }
    assert expected == tokenized
    decorated = _.replace(tokenized)
    assert {"test": "That&#x27;s what it&#x27;s about."} == decorated


def test_hackability():
    """
    Make sure that backslashing doesn't let me inject script tags.
    """
    parts = {"test": r"\<script\>alert('Hack!);\</script\>"}
    _ = Backslashes()
    tokenized = _.insert(parts)
    decorated = _.replace(tokenized)
    assert {"test": "&lt;script&gt;alert('Hack!);&lt;/script&gt;"} == decorated
