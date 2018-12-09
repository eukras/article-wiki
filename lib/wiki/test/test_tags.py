"""
Tags are the placeholders for index references.
"""

from .context import lib  # noqa: F401

from lib.wiki.index import Index
from lib.wiki.outline import Outline, default_counters
from lib.wiki.placeholders import DELIMITER
from lib.wiki.tags import Tags, split_pattern
from lib.wiki.utils import trim


def test_split_pattern():
    assert split_pattern("#[Tag]") == ("Tag", 'tag', '', '')
    assert split_pattern("#[Tag, subtag]!") == (
        "Tag", 'tag', 'subtag', '!')
    assert split_pattern("#[tags:tag]") == ("tags", 'tag', '', '')
    assert split_pattern("%[Tag]") == ("Tag", 'Tag', '', '')


def test_constructor():
    parts = {
        'index': trim("""
            My Document!

            It contains a #[Tag] and a %[Tag].

            ` Part One
        """),
        'part-one': trim("""
            Or an #[alias: Tag, subtag]?
        """),
    }

    outline = Outline(parts, default_counters())
    index = Index(outline)
    tags = Tags(index)

    new_parts = tags.insert(parts)

    assert new_parts == {
        'index': trim("""
            My Document!

            It contains a %stag:1%s and a %stag:2%s

            ` Part One
            """) % (DELIMITER, DELIMITER, DELIMITER, DELIMITER),
        'part-one': trim("""
            Or an %stag:1%s
            """) % (DELIMITER, DELIMITER),
    }

    end_parts = tags.replace(new_parts)

    assert 'Tag<sup>i</sup>' in end_parts['index']
    assert 'Tag.<sup>ii</sup>' in end_parts['index']
