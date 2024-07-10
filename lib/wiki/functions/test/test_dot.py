from .context import lib  # noqa: F401

from lib.wiki.functions.dot import Dot
from lib.wiki.renderer import Html
from lib.wiki.utils import trim

# No SVG in initial conversion of ebooks.


def DISABLED_test_simplest_graph():  # <-- Restore when Dot() is added again.
    """
    Minimal sanity check.
    """
    text = trim(
        """
        digraph G {
            Hello -> World
        }
        """
    )
    dot = Dot([], text)
    svg = dot.html(Html())
    for _ in ["<svg", "Hello", "World", "</svg>"]:
        assert _ in svg
