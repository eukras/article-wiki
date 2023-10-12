"""
Some functions that are widely used.
"""

import collections
import pytz
import random
import re

from datetime import datetime
from dateutil import parser
from functools import reduce
from typing import Union

from lib.wiki.placeholders import strip_placeholder_delimiters


DATE_FORMAT_ISO8601 = "%Y-%m-%dT%H:%M:%S%z"


def clean_document(parts_dict):
    """
    Make sure the input dictionary is unicode, and contains no
    placeholder symbols, and has consistent line endings.

    {'index': _, 'image.jpg': _} becomes {'index': _}
    {'index.txt': _, 'image.jpg': _} becomes {'index': _}
    """
    parts, files = {}, []
    for key, text in parts_dict.items():
        keyparts = key.split('.')
        if len(keyparts) == 1:
            parts[str(key)] = clean_text(text)
        elif len(keyparts) == 2:
            identifier, suffix = keyparts
            if suffix in ['txt']:
                parts[str(identifier)] = clean_text(text)
            elif suffix in ['png', 'jpg']:
                files += [str(key)]
            else:
                pass
        else:
            pass
    return (parts, files)


def clean_text(text):
    """
    Strip placeholder characters, and normalize line endings.
    """
    return strip_placeholder_delimiters(
        str(text.replace('\r\n', '\n').replace('\r', '\n'))
    ).strip()


def compose(functions):
    """
    Chain together a list of 1-to-1 functions.
    """
    assert all([isinstance(_, collections.abc.Callable) for _ in functions])

    def composer(fn_1, fn_2): return lambda _: fn_1(fn_2(_))

    def initialiser(_): return _

    return reduce(composer, functions, initialiser)


def count_words(text):
    """
    Approximate (i.e. hackish, inaccurate) word count.

    @todo Better to count from finished HTML.
    @todo Needs options to keep/omit footnotes and bibliography.
    """
    return len(re.findall(r'[\w\_\']+', text))


def html_escape(text):
    """
    Produce entities within text.
    """
    html_escape_table = {
        ">": "&gt;",
        "<": "&lt;",
        # "'": "&apos;",
        # '"': "&quot;",
        "&": "&amp;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


def get_option(options, index, of_type='all', default=''):
    """
    Get the nth option of a particular type (if specified)

    - 'combine' means treat the options as a single string (index is ignored)
    - 'all' means all options
    - 'digits' means all integers
    - 'dimension' options are decimals with a CSS units suffix ('%' or 'em').

    To add:

    - regexps or filters, and recreate these.
    """

    def css_dimension(value):
        """
        Ensure format is e.g. 5em, 5%, auto.

        @used self.get_option().
        """
        if value.endswith('%'):
            return "%d%%" % max(1, min(99, int(value[:-1])))
        elif value.endswith('em'):
            return "%dem" % max(1, min(99, int(value[:-2])))
        else:
            return "auto"

    if of_type in ('dimension', 'digits', 'combine'):
        use_type = of_type
    else:
        use_type = 'string'
    if use_type == 'combine':
        return ' '.join(options)
    if use_type == 'dimension':
        opts = [_ for _ in options if _.endswith('%') or _.endswith('em')]
        value = opts[index - 1] if index <= len(opts) else default
        return css_dimension(value) if value else ''
    elif use_type == 'digits':
        opts = [
            _ for _ in options
            if intify(_, default=None) is not None
        ]
        value = opts[index - 1] if index <= len(opts) else default
        return intify(value)
    else:
        value = options[index - 1] if index <= len(options) else default
        return value


def intify(x, default=0):
    """
    Integers from arbitrary input, else default value
    """
    digits = re.sub('[^0-9]', '', str(x))
    return int(digits) if digits != '' else default


def one_line(text: str) -> str:
    """
    All continuous whitespace (incl. tabs, line breaks) becomes a single
    space. AKA normalise spacing.
    """
    return re.sub(r'\s+', ' ', text.strip())


def parse_date(date: str, tz_name: str) -> Union[datetime, None]:
    """
    If this can be converted to a Datetime, then do so;
    return as UTC in ISO8601 format.

    Args:
        date: "1 Jan 2019"
        tz_name: "Australia/Sydney"
    Return:
        2018-12-31T13:01:00+0000
    """
    try:
        tz_local = pytz.timezone(tz_name)
        tz_utc = pytz.timezone('UTC')
        local = parser.parse(date)
        utc = tz_local.localize(local).astimezone(tz_utc)
        return utc.strftime(DATE_FORMAT_ISO8601)
    except ValueError:
        return None


def format_date(date: str, tz_name: str, date_fmt: str) -> str:
    """
    Args:
        date: 2018-12-31T13:01:00+0000  # <-- UTC ISO_8601
        tz_name: "Australia/Sydney"
        date_fmt: "%d %b %Y"
    Return:
        01 Jan 2019
    """
    try:
        tz_local = pytz.timezone(tz_name)
        utc = datetime.strptime(date, DATE_FORMAT_ISO8601)
        local = utc.astimezone(tz_local)
        return local.strftime(date_fmt)
    except ValueError:
        return "[Invalid Date]"


def pipe(objects: list, method_name: str, argument: str) -> str:
    """
    Compose object methods together and call with the specified argument.
    All functions must have a scalar argument and result, str -> str.
    """
    assert all([hasattr(_, method_name) for _ in objects])
    composition = compose([getattr(_, method_name) for _ in objects])
    return composition(argument)


def pluralize(number: int, singular: str, plural: str = "") -> str:
    """
    Super simple pluralization.
    """
    if number == 1:
        return "%d %s" % (number, singular)
    else:
        if plural != "":
            return "%d %s" % (number, plural)
        else:
            return "%d %ss" % (number, singular)


def random_slug(prefix: str) -> str:
    """
    Used for DEMO blocks.
    """
    return str(prefix) + str(random.randrange(100000000, 999999999))


def split_options(options: str) -> str:
    """
    "(opt1,opt 2 , opt  3) " --> ['opt1', 'opt 2', 'opt  3']
    """
    if not options:
        return []
    text = options.strip('() ')
    opts = [_.strip() for _ in text.split(',') if _ != '']
    return opts


def trim(text: str) -> str:
    """
    Strip empty lines at the start and end.
    Remove the leading whitespace of the first line from all lines.

    @todo: Make it minimum leading whitespace.
    """
    # Remove empty lines at start and end.
    body = trim_lines(text)
    # Count leading spaces in the first line.
    leading, _ = re.split(r'\S', body, 1)
    ltrim_cols = len(leading)
    # Trim that number of leading spaces from all lines.
    lines = [line[ltrim_cols:] for line in body.splitlines()]
    return "\n".join(lines)


def trim_lines(text):
    """
    Remove blank lines from start and end. Preserve leading whitespace on
    non-empty lines.
    """
    revlines = []
    hit = False
    for line in reversed(text.splitlines()):
        hit = hit or not line.strip() == ''
        if hit:
            revlines.append(line)
    lines = []
    hit = False
    for line in reversed(revlines):
        hit = hit or not line.strip() == ''
        if hit:
            lines.append(line)
    return "\n".join(lines)
