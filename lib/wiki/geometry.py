import collections
import re

from pprint import pprint

from lib.wiki.utils import one_line

"""
Functions for processing text structures.

Note wiki.test.geometry.py.
"""

# ------------------------------------------------------------
# Simple divisions

def get_non_empty_lines(text):
    """
    Remove non-empty lines, trim remainder.
    """
    return [_.strip() for _ in re.split("\n+", text) if _.strip() != ""]

def get_words(text):
    """
    Extract words from a string for matching words from other strings
    "Fred's shed" becomes ["freds", "shed"].  @todo... Check slugify for
    transliteration.
    """
    cleanup = text.replace("'", '').replace('_', ' ').lower()
    words = re.findall(r'\w+', cleanup, re.UNICODE)
    return words

def get_paragraphs(text):
    """
    Split a string into groups of lines delimited by at least two newlines.
    """
    return [x.strip() for x in re.split('\n{2,}', text.strip())]

# ------------------------------------------------------------
# Dividing up structures

def split_to_array(text, prefixes, capture_characters=True):
    """
    ? This
    / is
    ? 
    / a block

    Note line 3 is 1 char in length; must match a space OR a line ending.

    For prefixes = '?/=':
    With capture_characters:
        [('?', 'This'), ('/', 'is'), ('?', ''), ('/', 'a block')]
    Without:
        ['This', 'is', '', 'a block']
    """
    # Retain the first prefix if present
    r1 = re.compile("[%s](?: ?|$)" % re.escape(prefixes))
    if r1.match(text): # at start of string, vs. search()
        prefix, content = [text[0]], text[2:]
    else:
        prefix, content = [prefixes[0]], text
    if capture_characters:
        # Split with brackets captures the leading chars...
        r2 = re.compile("\n([%s])(?: ?|$)" % re.escape(prefixes))
        lines = [one_line(_) for _ in r2.split(content)]
        l = prefix + lines # So: char, line, char, line...
        # Convert to [(char, line), (char, line)... ]
        out = [tuple(l[i:i+2]) for i in range(0, len(l), 2)]
    else:
        r2 = re.compile("\n[%s](?: ?|$)" % re.escape(prefixes))
        out = [one_line(_) for _ in r2.split(content)]
    return out

def split_to_dictionary(text, prefix='$', delimiter='='):
    """
    Like split_to_array, but with leaders that become keys.

    $ key1 = value1
    $ key2 = value2

    {'key1': 'value1',
     'key2': 'value2'}
    """
    lines = split_to_array(text, prefix, capture_characters=True)
    out = {}
    for char, tail in lines:
        parts = tail.split(' %s ' % delimiter)
        if len(parts) == 2:
            out[parts[0].strip()] = one_line(parts[1].strip())
    return out

def split_to_recursive_array(text, prefix):
    """
    Split bullets into nested lists:

    * X
    * * X

    ['X', ['X']]
    """
    return collate_lines_by_prefix(
        split_to_array(text, prefix, capture_characters=False),
        prefix
        )

def collate_lines_by_prefix(lines, prefix):
    """
    Recusor for split_to_recursive_array.
    """
    array = []
    inner = []
    for line in lines:
        if line[0:len(prefix)] == prefix:
            inner.append(line[len(prefix):])
        else:
            if inner:
                array.append(collate_lines_by_prefix(inner, prefix))
                inner = []
            array.append(line)
    if inner:
        array.append(collate_lines_by_prefix(inner, prefix))
    return array

# ------------------------------------------------------------
# General transformations

def flatten(list_):
    """
    Return elements of an array in depth-first order.

    * X
    * * Y
    * Z

    ['X', 'Y', 'Z']
    """
    flat = []
    for item in list_:
        if isinstance(item, collections.Iterable) and not isinstance(item, str):
            flat += flatten(item)
        else:
            flat.append(item)
    return flat
