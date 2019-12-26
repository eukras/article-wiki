"""
Cross-references take the document outline and markup links between the
different parts of the document, of the form:

@[other heading] or @[-other heading] (for shorthand).
"""

from .context import lib  # noqa: F401

from lib.wiki.cross_references import CrossReferences
from lib.wiki.outline import Outline, default_counters
from lib.wiki.utils import trim


def test_replace():
    """
    Includes testing link creation.
    """
    parts = {
        'index': trim("""
            Test document

            - The Simple Test
            - The More Complex Test
            """),
        'test': trim("""
            This is a @[simple] test.

            This is a @[-more complex] test.
            """),
        }

    outline = Outline(parts, default_counters())
    placeholders = CrossReferences(parts, outline)

    tokenized = placeholders.insert(parts)
    html_parts = placeholders.replace(tokenized)
    out = html_parts['test']

    assert 'The Simple Test' in out
    assert '&sect;2' in out  # <-- complex uses shorthand
    assert 'the-simple-test' in out
    assert 'the-more-complex-test' in out
