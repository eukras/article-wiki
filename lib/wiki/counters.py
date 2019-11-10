"""
Counters in several numbering styles, using iterators.

counter = new_counter(u'a')  <-- Any of 1|a|A|i|I|g|G|*
next(counter) == u'a'
next(counter) == u'b'  # <-- and so on.

counter = RomanNumerals(u'xi', True)  # <-- count_from, is_uppercase?
next(counter) == u'XI'
next(counter) == u'XII'  # <-- and so on.

@todo: Update to __next__ for Python 3.
"""

import roman


ROMAN_LETTERS = 'abcdefghijklmnopqrstuvwxyz'
GREEK_LETTERS = 'αβγδεζηθικλμνξοπρστυφχψω'
SYMBOL_MARKERS = '*†‡§‖¶'


def new_counter(label='1'):
    """
    Factory method: Creates a counter by its CLASSES label. Use an uppercase
    letter to get an uppercase counter.

    Possible values: 1 A a G g I i *

    $ OUTLINE = 1.1.1.1.1.1  # <-- Default outline numbering is legal style.

    | * | Footnotes in front matter
    | 1 | Regular footnotes
    | a | Index/Tag numbering
    """
    uppercase = True
    return {
        'A': Letters('a', uppercase, ROMAN_LETTERS),
        'a': Letters('a', not uppercase, ROMAN_LETTERS),
        'G': Letters('α', uppercase, GREEK_LETTERS),
        'g': Letters('α', not uppercase, GREEK_LETTERS),
        'I': RomanNumerals('i', uppercase),
        'i': RomanNumerals('i', not uppercase),
        '*': Symbols('*'),
        }.get(label, Numbers(1))  # <-- Default.



class Numbers(object):
    """
    1, 2, 3, ... 9, 10, 11, ... 99, 100, 101, ...

    Uppercase is ignored, obviously; it's just there for a consistent
    interface among the counters.
    """
    def __init__(self, value='1', uppercase=False):
        self.value = int(value)

    def __iter__(self):
        return self

    def __next__(self):
        _ = self.value
        self.value += 1
        return str(_)


class RomanNumerals(object):
    """
    Just use integers 1..4999, and convert to/from Roman as needed.

    I, II, III, IV, V, VI, VII, VIII, IX, XI, XII, XIII, XIV, ...
    """

    def __init__(self, value='i', uppercase=False):
        """
        Only accept significant characters; however, our only interest is in
        counting from 'i', and no other verification is applied.

        No zero exists, so we post-increment the numbers; and for simple
        counting purposes, we can restart after 4999.
        """
        assert isinstance(value, str)
        try:
            self.value = int(roman.fromRoman(value.upper()))
        except roman.RomanError:
            pass  # <-- leave self.value at default.
        self.uppercase = bool(uppercase)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            numeral = str(roman.toRoman(self.value))  # <-- returns uppercase
            self.value += 1
        except roman.RomanError as e: # <-- Out of range; start again.
            # print e
            numeral = 'I'
            self.value = 2
        return numeral if self.uppercase else numeral.lower()


class Letters(object):
    """
    a, b, c, ... z, aa, ab, ... az, ba, bb, ...
    """
    def __init__(self, value='a', uppercase=False, pool=ROMAN_LETTERS):
        assert isinstance(value, str) or value is None
        self.value = value.lower() if value is not None else pool[0]
        self.uppercase = bool(uppercase)
        self.pool = pool

    def __iter__(self):
        return self

    def __next__(self):
        _ = self.value
        self.value = letter_increment(self.value, self.pool)
        return _.upper() if self.uppercase else _


class Symbols(object):
    """
    Following the convention for footnotes in front matter (which will be few),
    we use a sequence of symbols that are repeated on each loop through. See
    symbol_increment().

    Uppercase is ignored, obviously; it's just there for a consistent
    interface among the counters.
    """
    def __init__(self, value='*', uppercase=False, pool=SYMBOL_MARKERS):
        assert isinstance(value, str) or value is None
        self.value = value
        self.pool = pool

    def __iter__(self):
        return self

    def __next__(self):
        _ = self.value
        self.value = symbol_increment(self.value, self.pool)
        return _


#  ---------------------
#  Incrementor functions
#  ---------------------

def letter_increment(value, pool):
    """
    For lowercase letters we should see:

    a, b, ... z, aa, ab, ... az, ba, ... zz, aaa, ... etc

    Note this works for any sequence of character, incl. uppercase, hex, etc.
    """
    if value is None or len(value) == 0:
        return pool[0]
    if value[-1] == pool[-1]:  # <-- e.g. 'z'
        return letter_increment(value[:-1], pool) + pool[0]
    else:
        return value[:-1] + pool[pool.find(value[-1]) + 1]

def symbol_increment(value, pool):
    """
    If the pool were SYMBOLS '*†‡', we would see:

    *, †, ‡, **, ††, ‡‡, ***, †††, ‡‡‡, ...
    """
    if value is None or len(value) == 0:
        return pool[0]
    if value[-1] == pool[-1]:  # <-- e.g. '¶'
        return pool[0] * (len(value) + 1)
    else:
        return pool[pool.find(value[-1]) + 1] * len(value)
