# Generate a book cover

# Title (Bold, 120/180px)
# Subtitle (Italic, 96/130px)  # <-- Later
# ...
# Author (Italic, 96/130px)

import os
import re

from PIL import Image, ImageDraw, ImageFont

# Configuration

HEIGHT = 2200
WIDTH = 1600
MARGIN_HEIGHT = 300
MARGIN_WIDTH = 200

FOREGROUND = (248, 248, 248)  # <-- Alabaster
BACKGROUND = (160, 184, 160)  # <-- Norway, Summer Green, Pewter

SHADOW = (154, 174, 154)
TITLE_OFFSET = 8
AUTHOR_OFFSET = 5

TITLE_FONT = 'IBMPlexSerif-Bold.ttf'
TITLE_FONT_SIZE = 120

AUTHOR_FONT = 'IBMPlexSerif-Bold.ttf'
AUTHOR_FONT_SIZE = 80

LINE_HEIGHT = 1.10


def make_epub_cover(title: str, author: str,
                    font_dir: str, tpl_path: str, file_path: str):

    assert os.path.exists(tpl_path)

    cover = Image.open(tpl_path).convert('RGB')
    draw = ImageDraw.Draw(cover)

    text_width = WIDTH - (2 * MARGIN_WIDTH)
    text_center = MARGIN_WIDTH + (text_width / 2)

    title_font_path = os.path.join(font_dir, TITLE_FONT)
    author_font_path = os.path.join(font_dir, AUTHOR_FONT)
    assert os.path.exists(title_font_path)
    assert os.path.exists(author_font_path)

    title_words = re.findall(r'\S+', title)
    author_words = re.findall(r'\S+', author)

    title_font = ImageFont.truetype(title_font_path, TITLE_FONT_SIZE)
    title_lines = fit_words(title_font, title_words, text_width)
    title_line_height = line_height(title_font, LINE_HEIGHT)

    author_font = ImageFont.truetype(author_font_path, AUTHOR_FONT_SIZE)
    author_lines = fit_words(author_font, author_words, text_width)
    author_line_height = line_height(author_font, LINE_HEIGHT)

    # Title
    for number, line in enumerate(title_lines, start=0):
        text = ' '.join(line)
        line_width, _ = title_font.getsize(text)
        x = text_center - (line_width / 2)
        y = MARGIN_HEIGHT + (number * title_line_height)
        draw.text(
            (x + TITLE_OFFSET, y + TITLE_OFFSET),
            text,
            font=title_font,
            fill=SHADOW
            )
        draw.text((x, y), text, font=title_font, fill=FOREGROUND)

    # Author
    author_lines.reverse()
    for number, line in enumerate(author_lines, start=1):
        text = ' '.join(line)
        line_width, _ = author_font.getsize(text)
        x = text_center - (line_width / 2)
        y = HEIGHT - (MARGIN_HEIGHT + (number * author_line_height))
        draw.text(
            (x + AUTHOR_OFFSET, y + AUTHOR_OFFSET),
            text,
            font=author_font,
            fill=SHADOW
            )
        draw.text((x, y), text, font=author_font, fill=FOREGROUND)

    cover.save(file_path, 'JPEG', compress_level=0)


def line_height(font: ImageFont, multiplier: float):
    """
    Determine the line height to use for a given font, assuming 'hy' fills the
    vertical space.
    """
    w, h = font.getsize('hy')
    return h * multiplier


def fit_words(font: ImageFont, words: list, max_width: int) -> list:
    """
    Divide a list or words into the a list of lists of words representing the
    most evenly spaced lines with a given maximum width in pixels.

    TODO: Just split now, add even spacing later.
    """
    lines = []
    line = []
    for word in words:
        test_line = line + [word]
        test_string = ' '.join(test_line)
        width, _ = font.getsize(test_string)
        # print("WIDTH", test_string, width, "MAX", max_width)
        if width > max_width:
            lines += [line]
            line = [word]
        else:
            line += [word]
    lines += [line]
    return lines


# Testing
if __name__ == '__main__':
    make_epub_cover(
        "How Should Christians Think and Speak?",
        "Nigel Chapman",
        "/home/nigel/Web/article-wiki/resources/ttf",
        "/home/nigel/Web/article-wiki/resources/cover.png",
        "/home/nigel/cover.jpg"
    )
