"""
Divide a list of words into a list of lists of words representing the
most evenly spaced lines with a given maximum width in pixels.

1. Construct a set of options (trade completeness for efficiency)
2. Raggedness is the sum the squares of the leftover space in each line
3. Choose the option with minimum raggedness
"""

from typing import Any, Generator
from PIL.ImageFont import ImageFont


def simple_wrap(font: ImageFont, words: list, max_width_px: int) -> list[str]:
    """
    Just start a new line when we get to the end
    """
    lines = []
    line = []
    for word in words:
        test_line = line + [word]
        width = line_width(font, test_line)
        if width > max_width_px:
            if len(line) == 0:
                lines += [[word]]  # <-- Always at least one word
                line = []  # <-- Still
            else:
                lines += [line]
                line = [word]
        else:
            line += [word]
    lines += [line]
    return lines


def best_wrap(font: ImageFont, words: list, max_width_px: int) -> list[str] | None:
    """
    For each of a representative range of line wrapping options, produce a
    score of raggedness. Lowest score wins.
    """

    def sorting_function(lines):
        return raggedness(font, lines, max_width_px)

    options_list = list(options(font, words, max_width_px))
    sorted_options = sorted(options_list, key=sorting_function)
    return sorted_options[0] if len(sorted_options) > 0 else None


def step_ratios():
    return [n / 100 for n in range(100, 70, -2)]


def options(
    font: ImageFont, words: list, max_width_px: int
) -> Generator[list[str] | None, Any, Any]:
    """
    Don't calculate for every pixel width, just use a set of ratios. Generate
    simple line wrap for each option. If different from last, yield.
    """
    last_wrap = []
    for step in step_ratios():
        width_px = int(round(max_width_px * step))
        this_wrap = simple_wrap(font, words, width_px)
        if this_wrap != last_wrap:
            yield this_wrap
        last_wrap = this_wrap


def raggedness(font: ImageFont, lines: list, max_width_px: int) -> int:
    """
    Knuth-style raggedness, defined as sum of squares of available space
    in each line.
    """
    line_space = [max_width_px - line_width(font, line) for line in lines]
    return sum(_ * _ for _ in line_space)


def line_width(font: ImageFont, line: list) -> int:
    """
    Get the pixel width of ImageFont's rendering of a list of words.
    """
    return font.getlength(" ".join(line))
