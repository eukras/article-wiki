"""
Single point of definition for grammar variables.

Used in blocks and for self-documentation.
"""


class Config(object):
    """
    No dependencies.
    """

    subheads = '@'    # Indicate a subheading within a section
    nulls = '%^+-'    # Produce no output: comments, references, outlines
    setters = '$'     # Produce no output: settings
    quotes = '>'      # Block quotes
    notes = '"'       # Aside (margin note), Inline (visible) comment
    aligns = '.;,:~'  # Grouped aligment blocks
    lists = '*#_'     # Recursively nested lists, non-recursive icon lists
    tables = '!|'     # Tables, with format block, with format blocks
    glosses = '/'     # Interlinear translations
    quizzes = '?'     # Attach a question-and-answers block 
    caption = '='     # Attach a caption to the preceding block

    all_control_chars = (
        subheads + nulls + setters + quotes + notes + 
        aligns + lists + tables + quizzes + glosses + caption
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

    # See wiki.shorthand
    inline_shorthand_tuples = [
        ('/', 'em'),
        ('*', 'strong'),
        ('_', 'u'),
        ('`', 'kbd'),
    ]

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
