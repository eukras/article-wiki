"""
Sample data for use in various tests.
"""

from lib.wiki.utils import trim

minimal_document = {
    'index': trim("""
        Example document!

        ` Part One
        ` Part Two
        """),
    'part-one': trim("""
        Part One

        Here's the text for part one!
        """),
    'part-two': trim("""
        Part Two

        Here's the text for part two!
        """),
    }
