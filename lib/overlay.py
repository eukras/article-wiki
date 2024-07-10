# An overlay is a recipe for making an image with some text strings fitted into
# a specific set of positional frames of varying sizes, e.g.

# +---------------------------------------------------------------------------+
# |                       Title (Bold, 120/180px)                     75%,TOP |
# |                     Subtitle (Italic, 96/130px)                           |
# |                                                                           |
# |                                                                           |
# |                                                                           |
# |                                                                           |
# +---------------------------------------------------------------------------+
# |                                                               25%, BOTTOM |
# |                      Author (Italic, 96/130px)                            |
# +---------------------------------------------------------------------------+

import os
import re

from collections import ChainMap
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from lib.linewrap import best_wrap

ALIGN_TOP = "top"
ALIGN_MIDDLE = "middle"
ALIGN_BOTTOM = "bottom"
ALIGN_OPTIONS = [ALIGN_TOP, ALIGN_MIDDLE, ALIGN_BOTTOM]

COLOR_TEXT = (248, 248, 248)  # <-- Alabaster
COLOR_SHADOW = (154, 174, 154)  # <-- Some greeny gray thing
COLOR_BACKGROUND = (160, 184, 160)  # <-- Norway, Summer Green, Pewter

FONT_DIR = os.path.join(os.getcwd(), "resources/ttf")

FONT_REGULAR = "IBMPlexSerif-Regular.ttf"
FONT_BOLD = "IBMPlexSerif-Bold.ttf"
FONT_ITALIC = "IBMPlexSerif-Italic.ttf"

DEFAULT_LAYOUT = {
    "font_dir": FONT_DIR,
    "font_file": FONT_REGULAR,
    "font_size": 4,
    "font_scaling": 0.75,
    "font_base_size": 0.07,
    "line_ratio": 1.05,
    "margin_width_ratio": 0.04,
    "margin_height_ratio": 0.1,
    "text_color": COLOR_TEXT,
    "background_color": COLOR_BACKGROUND,
}

DEFAULT_FRAME = {"alignment": ALIGN_TOP, "height": 1, "text_gap_ratio": 0.5}

DEFAULT_TEXT = {
    "text_color": COLOR_TEXT,
    "shadow_color": COLOR_SHADOW,
    "shadow_offset_ratio": 0.1,
    "font_file": FONT_BOLD,
}


def make_cover(image: ImageDraw, strings: list, colors: list):
    assert len(strings) == 4  # <-- title, subtitle, author, date
    assert len(colors) == 2  # <-- text, shadow
    layout = {
        "text_color": colors[0],
        "shadow_color": colors[1],
        "frames": [
            {
                "height_ratio": 0.70,
                "alignment": ALIGN_TOP,
                "texts": [
                    {
                        "font_file": FONT_BOLD,
                        "font_size": 1,
                        "text": strings[0],
                    },
                    {
                        "font_file": FONT_ITALIC,
                        "font_size": 2,
                        "text": strings[1],
                    },
                ],
            },
            {
                "height_ratio": 0.30,
                "alignment": ALIGN_BOTTOM,
                "texts": [
                    {
                        "font_file": FONT_BOLD,
                        "font_size": 3,
                        "text": strings[2],
                    },
                    {
                        "font_file": FONT_REGULAR,
                        "font_size": 4,
                        "text": strings[3],
                    },
                ],
            },
        ],
    }
    make_overlay(image, layout)
    return image


def make_card(image: ImageDraw, strings: list, colors: list, byline: str):
    assert len(strings) == 2
    assert len(colors) == 2
    layout = {
        "text_color": colors[0],
        "shadow_color": colors[1],
        "margin_height_ratio": 0.1,
        "margin_width_ratio": 0.02,
        "font_base_size": 0.065,
        "line_ratio": 0.95,
        "frames": [
            {
                "height_ratio": 1,
                "alignment": ALIGN_MIDDLE,
                "texts": [
                    {"font_file": FONT_BOLD, "font_size": 1, "text": strings[0]},
                    {"font_file": FONT_ITALIC, "font_size": 2, "text": strings[1]},
                ],
            },
        ],
        "byline": byline,
    }
    make_overlay(image, layout)
    return image


def make_quote(image: ImageDraw, strings: list, colors: list, byline: str):
    assert len(strings) == 1
    assert len(colors) == 2
    layout = {
        "text_color": colors[0],
        "shadow_color": colors[1],
        "margin_height_ratio": 0.1,
        "margin_width_ratio": 0.02,
        "font_base_size": 0.065,
        "line_ratio": 0.95,
        "frames": [
            {
                "height_ratio": 1,
                "alignment": ALIGN_MIDDLE,
                "texts": [
                    {"font_file": FONT_ITALIC, "font_size": 1, "text": strings[0]}
                ],
            },
        ],
        "byline": byline,
    }
    make_overlay(image, layout)
    return image


def make_font(opts: dict, image: ImageDraw) -> ImageFont:
    """
    Create a font from font dir, file, and scaling
    """

    font_base_size = opts.get("font_base_size")
    font_scaling = opts.get("font_scaling")
    font_size = opts.get("font_size")
    font_ratio = font_scaling**font_size

    w, h = image.size
    image_length_px = max(w, h)

    font_size_px = int(round(font_base_size * font_ratio * image_length_px))

    font_dir = opts.get("font_dir")
    font_file = opts.get("font_file")
    font_path = os.path.join(font_dir, font_file)

    font = ImageFont.truetype(font_path, font_size_px)

    return font


def make_overlay(image, layout):

    layout_opts = ChainMap(layout, DEFAULT_LAYOUT)

    margin_width_ratio = layout_opts.get("margin_width_ratio")
    margin_height_ratio = layout_opts.get("margin_height_ratio")

    text_center = int(round(image.width / 2))
    text_width_px = int(round(image.width * (1 - (2 * margin_width_ratio))))
    margin_height_px = int(round(image.height * margin_height_ratio))

    max_width_px = max(image.width, image.height)

    body_height_px = image.height - (margin_height_px * 2)
    frame_offset_px = margin_height_px

    draw = ImageDraw.Draw(image)

    byline = layout_opts.get("byline")
    if byline:

        font_dir = layout_opts.get("font_dir")
        font_file = layout_opts.get("font_file")
        font_base_size = layout_opts.get("font_base_size")
        font_scaling = layout_opts.get("font_scaling")
        font_size = 5

        font_path = os.path.join(font_dir, font_file)
        font_ratio = font_scaling**font_size
        font_size_px = int(round(font_base_size * font_ratio * max_width_px))
        font = ImageFont.truetype(font_path, font_size_px)

        text_color = layout_opts.get("text_color")

        make_byline(image, font, byline, text_color)

    for frame in layout["frames"]:

        frame_opts = ChainMap(frame, layout, DEFAULT_FRAME, DEFAULT_LAYOUT)
        height_ratio = frame_opts.get("height_ratio")
        alignment = frame_opts.get("alignment")
        line_ratio = frame_opts.get("line_ratio")

        frame_height_px = int(round(body_height_px * height_ratio))

        text_height_px = 0
        store_font = {}
        store_lines = {}

        for number, text in enumerate(frame["texts"]):

            text_opts = ChainMap(
                text, frame, layout, DEFAULT_TEXT, DEFAULT_FRAME, DEFAULT_LAYOUT
            )

            font = make_font(text_opts, image)

            string = text_opts.get("text", "[placeholder]")
            words = re.findall(r"\S+", string)
            lines = best_wrap(font, words, text_width_px)

            store_font[number] = font
            store_lines[number] = lines

            text_gap_ratio = frame_opts.get("text_gap_ratio")

            line_height_px = int(round(font_height(font) * line_ratio))
            text_gap_px = int(round(line_height_px * text_gap_ratio))
            text_height_px += (line_height_px * len(lines)) + text_gap_px

        y = {
            ALIGN_TOP: frame_offset_px,
            ALIGN_MIDDLE: (
                frame_offset_px
                + int(round(frame_height_px / 2))
                - int(round(text_height_px / 2))
            ),
            ALIGN_BOTTOM: frame_offset_px + frame_height_px - text_height_px,
        }.get(alignment)

        for number, text in enumerate(frame["texts"]):

            text_opts = ChainMap(
                text, frame, layout, DEFAULT_TEXT, DEFAULT_FRAME, DEFAULT_LAYOUT
            )

            text_color = text_opts.get("text_color")
            shadow_color = text_opts.get("shadow_color")
            shadow_offset_ratio = text_opts.get("shadow_offset_ratio")

            font = store_font[number]

            line_height_px = int(round(font_height(font) * line_ratio))
            shadow_size_px = int(round(line_height_px * shadow_offset_ratio))
            text_gap_px = int(round(line_height_px * text_gap_ratio))

            lines = store_lines[number]

            for line in lines:

                text = " ".join(line)
                line_width = font.getlength(text)
                x = text_center - int(round(line_width / 2))
                draw.text(
                    (x + shadow_size_px, y + shadow_size_px),
                    text,
                    font=font,
                    fill=shadow_color,
                )
                draw.text((x, y), text, font=font, fill=text_color)

                y += line_height_px

            y += text_gap_px

        frame_offset_px += frame_height_px


def make_byline(image: Image, font: ImageFont, byline: str, color: tuple):
    """
    Site marker in bottom right corner.
    """
    left, top, right, bottom = font.getbbox(byline)
    w, h = right - left, bottom - top
    margin = int(round(h * 1.5))
    x = image.width - w - margin
    y = image.height - h - margin
    draw = ImageDraw.Draw(image)
    draw.text((x, y), byline, font=font, fill=color)


@lru_cache(maxsize=32)
def font_height(font: ImageFont):
    left, top, right, bottom = font.getbbox("hy")
    height = bottom - top
    return height
