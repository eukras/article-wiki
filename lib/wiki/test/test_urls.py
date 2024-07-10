from .context import lib  # noqa: F401

from lib.wiki.urls import Urls
from lib.wiki.placeholders import DELIMITER


def test_urls():
    """
    Test that URLs are matched and restored
    """
    url = r"https://example.org"
    parts = {"test": url}
    _ = Urls()
    tokenized = _.insert(parts)
    expected = {"test": DELIMITER.join(["", "ur:1", ""])}
    assert expected == tokenized
    decorated = _.replace(tokenized)
    expected = {"test": '<a href="%s" target="_blank">%s</a>' % (url, url)}
    assert expected == decorated


def test_emails():
    """
    Test that emails are matched and restored.
    """
    email = "hello@example.org"
    emailto = "mailto:%s" % email
    parts = {"test": email}
    _ = Urls()
    tokenized = _.insert(parts)
    expected = {"test": DELIMITER.join(["", "ur:1", ""])}
    assert expected == tokenized
    decorated = _.replace(tokenized)
    expected = {"test": '<a href="%s" target="_blank">%s</a>' % (emailto, email)}
    assert expected == decorated
