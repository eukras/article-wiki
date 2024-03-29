"""
Article Wiki: Module for identifying and processing text blocks.

The BlockList must:

- turn a string (a 'section') into a list of blocks.
- return that text in a canonical wiki format.
- return HTML via a specified renderer.

Each Block must:

- be instantiated with the section of text that was accepted.
- reformat itself into canonical wiki text.
- render HTML, using a renderer (an instance of Html).
"""

import re

from airium import Airium
from textwrap import shorten

from copy import copy
from jinja2 import Environment

from lib.slugs import slug

from lib.wiki.functions.base import \
    Articles, \
    Box, \
    Center, \
    Compact, \
    Indent, \
    Feature, \
    Footer, \
    Function, \
    Float, \
    Header, \
    Left, \
    Print, \
    Quote, \
    Right, \
    Text, \
    Verbatim, \
    Web, \
    Wrapper
from lib.wiki.functions.table import \
    Table

from lib.wiki.config import Config
from lib.wiki.geometry import \
    split_to_array, \
    split_to_dictionary, \
    split_to_recursive_array
from lib.wiki.renderer import \
    alert, \
    generate_table, \
    Html, \
    parse_table_data, \
    rule, \
    section_heading, \
    space, \
    tag
# from lib.wiki.icons import \
# expand_shorthand
from lib.wiki.placeholders import \
    is_placeholder
from lib.wiki.inline import \
    Inline
from lib.wiki.utils import \
    clean_text, \
    one_line, \
    random_slug, \
    split_options, \
    trim


class BlockList(object):
    """
    Marshalling class that manages block objects, and presents the only
    external access point for block use.

    > blocks = BlockList(text)
    > new_text = blocks.text()
    > new_html = blocks.html()
    """

    def __init__(self, text: str):
        """
        Process a wiki text into a list of blocks.
        """
        self.blocks = []
        self.process(text)

    def __iter__(self):
        "Loop through the blocks..."
        return iter(self.blocks)

    def process(self, text: str):
        """
        Check if the current cursor position is the start of:

        1. A FunctionBlock, either:
            a) Standalone (e.g. "TEXT ---" or "@ LOREM (5)")
            b) Or with wrappers (e.g. "CENTER (50%) : TEXT ---")
        2. A Paragraph-based Block, one of:
            a) Divider (e.g."- - -")
            b) CharacterBlock (e.g. "+ Subheading")
            c) Paragraph

        If so, create that block, move the cursor to the end of
        the text it contained, repeat until finished.
        """

        function_pattern = re.compile((
            r"([A-Z]+)\s+(\([^)]+\)\s)?\s*([%s])\3\3\s*\n"
        ) % re.escape(Config.delimiters))

        wrappers = {_.__name__.upper(): _ for _ in [
            Box,
            Center,
            Compact,
            Feature,
            Float,
            Footer,
            Indent,
            Header,
            Left,
            Print,
            Quote,
            Right,
            Web,
        ]}

        functions = {_.__name__.upper(): _ for _ in [
            Articles,
            Grid,
            Table,
            Text,
            Verbatim,
        ]}

        functions.update(wrappers)  # <-- Wrappers are functions too

        cursor, length = 0, len(text) - 1
        self.blocks = []

        while cursor < length:

            cursor = start_of_block(text, cursor)

            # FUNCTION (options) ---
            match = function_pattern.match(text, cursor)
            if match:
                name, options, div = match.groups()
                # Match the next ---\n, if one can be found
                end = text.find("\n" + (div * 3) + "\n", cursor)
                if end == -1:
                    # Else any ---, usually the end of the file.
                    end = text.find("\n" + (div * 3), cursor)
                if name in functions and end != -1:
                    new_cursor = end + 5
                    block_text = text[cursor:new_cursor].strip()
                    content = "\n".join(block_text.splitlines()[1:-1])
                    block = FunctionBlock(functions[name],
                                          split_options(options),
                                          div, content)
                    self.blocks.append(block)
                    cursor = new_cursor
                    continue

            # Paragraph-based blocks
            next_blank_line = text.find("\n\n", cursor)
            if next_blank_line == -1:  # <-- not found
                _ = text[cursor:].strip()  # <-- take all remaining text
                cursor = len(text)
            else:
                _ = text[cursor:next_blank_line].strip()
                cursor = next_blank_line

            if len(_) > 0:
                if _ in Config.dividers:
                    self.blocks += [Divider(_)]
                elif len(_) > 1:
                    if _[0] in Config.all_control_chars and _[1] == ' ':
                        self.blocks += [CharacterBlock(_)]
                    else:
                        self.blocks += [Paragraph(_)]
                else:
                    self.blocks += [Paragraph(_)]

    def dump(self):
        """
        Show current state for debugging.
        """
        return "\n".join([
            "%s: %s" % (block.__class__.__name__, block.content)
            for block in self.blocks
        ])

    def find(self, class_name, control_characters: str = None) -> list:
        """
        A quick way to filter for block types (more than one, e.g. "+-").
        """
        found = []
        for _ in self.blocks:
            if _.__class__.__name__ == class_name:
                if class_name == 'CharacterBlock':
                    if (_.control_character is None or
                            _.control_character in control_characters):
                        found += [_]
                else:
                    found += [_]
        return found

    def text(self):
        """"
        Return canonical wiki text, meaning:

        - No trailing whitespace
        - No leading or contiguous whitespace outside function blocks
        - No line wrapping.
        """
        return "\n\n".join([_.text() for _ in self.blocks])

    def title_and_summary(self):
        """
        Return the first block's content as title, if it is a paragraph or
        comment, then the second block's content as a summary, if it is a
        caption. Content will be trimmed with an ellipsis added, as one line.
        """
        title, summary = '', ''
        if len(self.blocks) > 0:
            if isinstance(self.blocks[0], Paragraph):
                title = one_line(shorten(self.blocks[0].content, 128,
                                         placeholder="..."))
            if isinstance(self.blocks[0], CharacterBlock):
                if self.blocks[0].control_character == '%':
                    title = one_line(shorten(self.blocks[0].content[2:], 128,
                                             placeholder="..."))
        if len(self.blocks) > 1:
            if isinstance(self.blocks[1], CharacterBlock):
                if self.blocks[1].control_character == Config.caption:
                    summary = one_line(shorten(self.blocks[1].content[2:], 128,
                                               placeholder="..."))
        return title, summary

    def pop_titles(self):
        """
        Return title and summary, removing from blocks.
        @todo: REFACTOR: Very similar to title_and_summary().
        """
        title, summary = '', ''
        if len(self.blocks) > 0:
            _ = self.blocks[0]
            if isinstance(_, Paragraph):
                title = _.content
                self.blocks.pop(0)
            if isinstance(_, CharacterBlock) and _.control_character == '%':
                title = _.content
                self.blocks.pop(0)
        if len(self.blocks) > 0:
            _ = self.blocks[0]
            if isinstance(_, CharacterBlock):
                if _.control_character == Config.caption:
                    summary = _.content[2:]
                    self.blocks.pop(0)
        return (str(shorten(title, 128, placeholder='...')),
                str(shorten(summary, 128, placeholder='...')))

    def html(self, numbering, slug, settings, fragment=False, preview=False):
        """
        Produce HTML, passing along any settings that were updated while
        processing any block.

        - A fragment has no title lines (rename: no_titles?).
          (Used in demo blocks.)
        - A preview has no section numbering in its title.
          (Used in the editor.)
        """
        renderer = Html({})
        renderer.settings = copy(settings)
        out = []
        if not fragment and slug != 'index':
            title, summary = self.pop_titles()
            nav_id = get_section_nav_id(numbering, slug)
            number = '.'.join([str(_) for _ in numbering])
            if summary != '':
                subtitle = renderer.inline.process(summary)
            else:
                subtitle = None
            out += [str(section_heading(nav_id, number, title, subtitle))]
        # Assemble
        local_settings = copy(settings)
        for _ in self.blocks:
            block_html, local_settings = _.html(renderer, local_settings)
            out += [block_html]
        return "\n\n".join(out)


def get_title_data(text: str, part_slug: str) -> (str, str, str, str):
    """
    Return titles info from any text section, allowing for the SLUG setting.

    Example text:

        Title

        = Summary

        $ SLUG = slug-name

    Args:
        text: the wiki text for a document part
        part_slug: the existing slug for this part

    Returns:
        a tuple of strings: (part_slug, title, title_slug, and summary)
    """
    blocks = BlockList(clean_text(text))
    title, summary = blocks.title_and_summary()
    title_slug = slug(title)
    for _ in blocks.find('CharacterBlock', '$'):
        settings = split_to_dictionary(_.text(), prefix='$', delimiter='=')
        if 'SLUG' in settings:
            title_slug = slug(settings['SLUG'])
    return part_slug, title, title_slug, summary


class Block(object):
    """
    A superclass, with methods common to all blocks.
    """

    def html_only(self, renderer, settings):
        "For when only the html is needed..."
        (html, settings) = self.html(renderer, settings)
        return html


class Paragraph(Block):
    """
    A block of plain wiki text. It may contain only a placeholder, in which
    case we don't wrap it in <p> tags.
    """

    def __init__(self, text: str):
        "Normalize spacing."
        self.content = one_line(text)

    def text(self):
        "For paragraphs there is only one line to wrap."
        return self.content

    def html(self, renderer, settings):
        "Just wrap in a paragraph tag (with inline formatting)."
        if is_placeholder(self.content):
            html = settings.replace(self.content)
        else:
            html = tag('p', settings.replace(self.content))
        return (html, settings)


class Divider(Block):
    """
    When the whole paragraph is a one-line pattern.
    """

    def __init__(self, text: str):
        "Strip and store."
        self.content = text

    def text(self):
        """
        As you were...
        """
        return self.content

    def html(self, renderer, settings):
        """
        Map divider patterns to HTML, which doesn't change.
        """
        html = {
            # Markers
            '*': '<p class="text-center text-large space"><span>✻</span></p>',
            '-': rule('div-solid div-center'),
            '* * *': trim("""
                <p class="text-center text-large big-space">
                    <span>✻ ✻ ✻</span>
                </p>
                """),
            '- - -': rule('div-solid'),
            '. . .': rule('div-dotted div-wide'),
            '= = =': rule('div-thick div-wide'),
            # Spacers
            '~': space(1),
            '~ ~': space(2),
            '~ ~ ~': space(3),
            '~ ~ ~ ~': space(4),
        }.get(self.content, '')
        return (html, settings)


class CharacterBlock(Block):
    """
    The main issue with rendering character blocks is line-wrapping properly
    when there are multiple lines involved, either:

    - recursive lines, or
    - lines that can be grouped with others that they follow, e.g. captions or
    alignment blocks.
    """

    def __init__(self, text):
        """
        Process the text for just this block; processors recieve the whole text
        including the first character
        """
        self.control_character = text[0]
        self.content = text

    def text(self):
        """
        Leave lines beginning with a control character unwrapped.
        """
        tuples = split_to_array(self.content, Config.all_control_chars)
        lines = [char + ' ' + one_line(line) for char, line in tuples]
        space_above = "\n" if self.control_character in Config.subheads else ""
        return space_above + "\n".join(lines)

    def html(self, renderer, settings):
        """
        Call the right layout function from the renderer...
        """
        renderer.settings = settings or {}
        html, _ = '', copy(renderer.settings)
        _ = self.control_character
        content = settings.replace(self.content)
        if _ in Config.nulls:
            html = ''
        elif _ in Config.setters:
            settings.read_settings_block(content)
        elif _ in Config.subheads:
            html = subhead_block(content, settings)
        elif _ in Config.quotes:
            html = quote_block(content, settings)
        elif _ in Config.notes:
            html = note_block(content, settings)
        elif _ in Config.caption:
            html = caption_block(content, settings)
        elif _ in Config.aligns:
            html = align_block(content, settings)
        elif _ in Config.lists:
            html = list_block(content, settings)
        elif _ in Config.tables:
            html = table_block(content, settings)
        elif _ in Config.quizzes:
            html = quiz_block(content, settings)
        elif _ in Config.glosses:
            html = gloss_block(content, settings)
        else:
            html = alert('Unrecognized control character: %s')
        return (html, settings)


class FunctionBlock(Block):
    """
    Generate canonical text and HTML for a function block; recursing into
    function block as neededV

    Some blocks just wrap others in HTML, e.g. the alignment blocks, and others
    reformat plain text. Wrappers should be chainable, with '|'. May as well
    recurse, for simplicity.

    @todo: In future, Functions should be given an option to reformat
    themselves canonically.
    """

    def __init__(self, function_class, options, divider, text: str):
        """
        Function, aguments, and dividers are specific to FunctionBlocks

        A wrapper contains blocks; a regular function contains text whose
        meaning is specific to the function being called.
        """
        assert hasattr(options, '__iter__')  # non-string iterable
        self.function_class = function_class  # <-- a class
        self.options, self.divider = options, divider
        self.content = text
        if issubclass(self.function_class, Wrapper):
            self.blocks = BlockList(self.content)

    def text(self):
        """
        Canonical form is almost the same as required form.

        - Omit the brackets entirely when there are no options given.
        """
        class_name = self.function_class.__name__.upper()
        if len(self.options) > 0:
            args = ', '.join(self.options)
            line = '%s (%s) %s' % (class_name, args, self.divider * 3)
        else:
            line = '%s %s' % (class_name, self.divider * 3)
        parts = [line]
        if issubclass(self.function_class, Wrapper):
            content = self.blocks.text()
        else:
            content = self.content
        if content != "":
            parts += [content]
        parts += [self.divider * 3]
        return '\n'.join(parts)

    def html(self, renderer, settings):
        """
        If the function is a wrapper, wrap HTML,
        If it is a function, generate HTML from content.
        """
        if issubclass(self.function_class, Wrapper):
            dummy_numbering, dummy_slug = ['0'], 'slug'
            inner_html = self.blocks.html(
                dummy_numbering, dummy_slug, settings, fragment=True
            )
            function = self.function_class(self.options, '')  # <-- ignore text
            html = function.wrap(inner_html)
        else:
            function = self.function_class(self.options, self.content)
            # settings.replace(self.content))
            html = function.html(renderer)
        return (html, settings)

# --------------------------------------
# FunctionBlocks that utilise BlockLists
# --------------------------------------


class Grid(Function):
    """
    GRID +++
    - Column 1, Row 1
    ---
    > Column 2, Row 1
    ===
    * Column 1, Row 2
    ---
    # Column 2, Row 2
    +++
    """

    def html(self, renderer):
        html_rows = []
        for row in [row.strip() for row in self.text.split("===")]:
            html_cells = []
            for cell in [cell.strip() for cell in row.split("---")]:
                blocks = BlockList(clean_text(cell))
                slug = random_slug('grid-')
                html = blocks.html([0], slug, renderer.settings, fragment=True)
                html_cells.append(html)
            html_rows.append(html_cells)

        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
            <table class="table table-condensed">
            <tbody>
            {% for html_row in html_rows %}
                <tr>
                    {% for html_cell in html_row %}
                    <td>{{ html_cell|safe }}</td>
                    {% endfor %}
                </tr>
            {% endfor %}
            </tbody>
            </table>
        """))

        return tpl.render(html_rows=html_rows)


# ------------------------------
# Module-level utility functions
# ------------------------------


def start_of_block(text: str, cursor: int) -> int:
    """
    The start of a block is a non-whitespace character preceeded by '\n\n' (or
    fewer newlines if cursor < 2.

    If the cursor is not at the start of a block, advance until it is.

    Assumes \t has been expanded to spaces and newlines are just \n (no \r);
    see wiki.clean_input().
    """
    _ = min(len(text), max(0, cursor))  # <-- 0..len(text)
    while _ < len(text):
        two_preceding_newlines = any([
            _ == 0,
            _ == 1 and text[0] == '\n',
            text[_ - 2:_] == '\n\n'
        ])
        if two_preceding_newlines and text[_] not in ' \n':
            return _
        else:
            _ += 1
    return _


def get_section_nav_id(numbering, title):
    """
    #nav_id is the section anchor
    """
    number = '.'.join([str(_) for _ in numbering])
    return number + '_' + str(title)


def align_block(content, settings):
    """
    There is space around each set of alignment statements, but not
    between the individual lines. Ths means divs are wrapped in an outer
    paragraph tag.
    """
    lines = split_to_array(content, Config.aligns)
    out = []
    for char, line in lines:
        class_name = {
            '.': 'text-left',
            ';': 'text-center',
            ',': 'text-right',
            ':': 'indent',
            '~': 'indent-hanging',
        }.get(char, '')
        out += [tag('div', line, class_name)]
    if len(out) > 0:
        return "".join([
            '<div class="wr-align-block space">',
            '<span>',
            ''.join(out),
            '</span>',
            '</div>',
        ])
    else:
        return ''


def note_block(content, settings):
    """
    " block note
    """
    lines = split_to_array(content, prefixes=Config.notes)

    def note_line(part):
        char, text = part
        if char == '"':
            return tag('p', text, 'note')
        else:
            return alert(content)
    out = map(note_line, lines)
    return "\n".join(out)


def subhead_block(content, settings):
    """
    Just one level of subheadings for now, no captions.
    @ Subheading
    """
    lines = split_to_array(content, prefixes=Config.subheads)

    def subhead_line(part):
        char, text = part
        if char == '@':
            return tag('p', text, 'subhead')
        else:
            return alert(content)
    out = map(subhead_line, lines)
    return "\n".join(out)


def quote_block(content, settings):
    """
    Config.quotes:
    > blockquote
    plus:
    = caption
    """
    lines = split_to_array(content, prefixes=Config.quotes + Config.caption)
    out = []
    for char, content in lines:
        if char == '>':
            out += [tag('blockquote', content)]
        elif char == Config.caption:
            out += [tag('p', content, 'caption')]
    if len(out) > 0:
        return "\n".join(out)
    else:
        return ""


def caption_block(content, settings):
    """
    = Caption
    """
    lines = split_to_array(content, prefixes=Config.caption)
    out = []
    for char, content in lines:
        if char == Config.caption:
            out += [tag('p', content, 'caption')]
    if len(out) > 0:
        return "\n".join(out)
    else:
        return ""


def list_block(text, settings):
    """
    * Bullets 1
    * * Bullets 2
    Or:
    # Numbers 1
    # # Numbers 2
    Or:
    _ Custom Markers (checkboxes by default)
    _ _ Custom Markers
    """
    def list_block_recursor(char, items, settings, depth=1):
        """
        Recursion handler for list_block().

        $ NUMBERING = ... is the next item to count from.
        $ CONTINUE = ... is the count to use if NUMBERING = continue
        """
        inline = Inline()
        list_tag = 'ol' if char == '#' else 'ul'
        properties = ['']
        if list_tag == 'ol' and depth == 1:
            numbering = settings.get('NUMBERING', '')
            if numbering.isdigit():
                properties += ['start="%s"' % numbering]
                settings.set('CONTINUE', int(numbering))
                settings.set('NUMBERING', '')
            elif numbering == 'continue':
                properties += ['start="%s"' % settings.get('CONTINUE')]
                settings.set('NUMBERING', '')
            else:
                settings.set('CONTINUE', 1)
        if char == '_':
            properties += ['class="checkboxes"']

        # XHTML (for ebooks) requires that a child list appears inside the
        # preceeding <li> rather than inside it's own <li>. So we'll accumulate
        # display_items distinct from structural items, and join these into an
        # HTML list at the end.
        open_tag = "<%s%s>" % (list_tag, ' '.join(properties))
        display_items = []
        for item in items:
            if isinstance(item, list):
                # There should always be a preceding element when we reach a
                # sublist. Append to that:
                if len(display_items) > 0:
                    last = len(display_items) - 1
                    sub_list = list_block_recursor(
                        char, item, settings, depth + 1
                    )
                    display_items[last] += sub_list
            else:
                display_items += [inline.process(item)]
                if list_tag == 'ol' and depth == 1:
                    settings.set('CONTINUE', settings.get('CONTINUE') + 1)
        close_tag = "</%s>" % list_tag
        lines = [open_tag]
        for item in display_items:
            lines.append("<li>" + item + "</li>")
        lines.append(close_tag)
        return "\n".join(lines)

    # May need a character-aware recursor to support mixed levels.
    char = text[0]
    items = split_to_recursive_array(text, char + ' ')
    return list_block_recursor(char, items, settings)


def column_block(text, settings):
    """
    Simple columns (maximum of 4):

    ] Column 1
    ] Column 2

    # Or 12-column grids? @todo
    #
    # ] 3 ] Col 1.
    # ] 9 ] Column Number Two.
    """
    char = text[0]
    parts = split_to_array(text, prefixes=char)
    html = ''
    parts = parts[:4]  # <-- max. 4 parts
    twelfths = round(12 / len(parts))
    bootstrap_class = 'col-md-%d' % twelfths
    for char, content in parts:
        html += tag('p', content, 'float-left %s' % bootstrap_class)
    html += "<div style=\"clear: both\"></div>"
    return html


def quiz_block(text, settings):
    """
    Build HTML from text.
    """
    inline = Inline()
    q_html, a_html = [], [];
    for char, line in split_to_array(text, '?=', capture_characters=True):
        if char == '?':
            q_html.append(inline.process(line))
        if char == '=':
            a_html.append(inline.process(line))
    __ = Airium()
    with __.div(klass='quiz'):
        if q_html:
            with __.ol(klass='questions'):
                for line in q_html:
                    with __.li():
                        __(line)
        if a_html:
            with __.ol(klass='answers'):
                for line in a_html:
                    with __.li():
                        __(line)
    return str(__)


def gloss_block(text, settings):
    """
    Build HTML from text.
    """
    inline = Inline()
    char = text[0]  # '/', as used here
    gloss = []
    num = None
    for _, line in split_to_array(text, char):
        parts = line.split(" %s " % char)
        if len(parts) == 1:
            num = parts.pop(0)
        else:
            source_html = inline.process(parts.pop(0))
            translations_html = [inline.process(part) for part in parts]
            if num is not None:
                gloss += [[(str(num), ''), (source_html, translations_html)]]
                num = None
            else:
                gloss += [[(source_html, translations_html)]]

    env = Environment(autoescape=True)
    tpl = env.from_string(trim("""
        <div class="gloss">
        {% for translation_group in gloss %}
            <div class="phrase-group">
                {% for source_html, translations in translation_group %}
                <div class="phrase">
                    <div class="source">{{ source_html|safe }}</div>
                    {% for translation_html in translations %}
                    <div class="translation">{{ translation_html|safe }}</div>
                    {% endfor %}
                </div>
                {% endfor %}
            </div>
        {% endfor %}
        </div>
    """))

    return tpl.render(gloss=gloss)


def table_block(text, settings):
    """
    Generate simple tables.
    """
    char = text[0]
    divisions = split_to_array(text, Config.tables, capture_characters=False)
    has_headers = (char == '!')
    data, options = parse_table_data(divisions, has_headers)
    return generate_table(data, options)
