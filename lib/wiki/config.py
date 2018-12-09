"""
Single point of definition for 'grammar'.

Used in blocks and for self-documentation.
"""


class Config(object):
    """
    No dependencies.
    """

    nulls = '%^`'          # Produce no output
    setters = '$'          # Produce no output; change local settings
    headers = '+-"'        # Headings within a document part
    quotes = '>='          # Block quotes, pull quotes, captions
    notes = "'?"           # Aside (margin note), Inline (visible) comment
    aligns = '.;,:~()'     # Grouped formatting divs
    lists = '*#_'          # Recursively nested lists, un/ordered
    tables = '!|'          # Tables, with format block, with format blocks
    glosses = '/'          # Interlinear translations
    figures = '@'          # Embed a printable file
    caption = '='          # Attach a caption to the preceding block

    captions = '+>!|@'     # Blocks that captions or bylines may follow

    # Characters that can be repeated once (with spacing) to define a inline
    # heading (also: u'=', but handled specially):

    leaders = "~'?"

    all_control_chars = (
        nulls + setters + headers + quotes + notes + aligns +
        lists + tables + figures + caption + glosses
        )

    dividers = [
        '*', '* * *',
        '@', '@ @ @',
        '.', '. . .',
        '-', '- - -',
        '=', '= = =',
        '~', '~ ~', '~ ~ ~', '~ ~ ~ ~',
        ]

    delimiters = '-=>+:%"/'

    settings = {
        'OUTLINE': '1.a.i.g',
        'NUMBERING': '1',
    }

    punctuation = ",.?!:;·"

    # See wiki.icons
    fontawesome_icon_aliases = {
        ')': 'smile-o',
        '(': 'frown-o',
        '|': 'meh-o',
        '/': 'pencil',
        '*': 'star',
        '!': 'exclamation-triangle',
        '?': 'question-circle',
        'i': 'info-circle',
        '_': 'square-o',
        'n': 'times',
        'y': 'check',
        'N': 'times-circle',
        'Y': 'check-circle',
        'q': 'quote-left',
        'h': 'heart',
        't': 'tag',
        'f': 'flag',
        '+': 'plus-circle',
        '-': 'minus-circle',
        'u': 'arrow-up',
        'd': 'arrow-down',
        'l': 'arrow-left',
        'r': 'arrow-right',
        'U': 'arrow-circle-up',
        'D': 'arrow-circle-down',
        'L': 'arrow-circle-left',
        'R': 'arrow-circle-right',
    }

    # See wiki.shorthand
    inline_shorthand_tuples = [
        ('/', 'i'),
        ('*', 'b'),
        ('_', 'u'),
        ('`', 'tt'),
        ('|', 'var'),
    ]
