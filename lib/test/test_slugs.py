from .context import lib  # noqa: F401

from lib.slugs import slug


def test_apostrophes():
    assert slug('Its charms are many') == 'its-charms-are-many'
    assert slug("It's a marvelous day") == 'its-a-marvelous-day'
