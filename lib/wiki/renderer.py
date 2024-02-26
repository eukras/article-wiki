"""
Render HTML output of numerous kinds, usually with awareness of settings.

Render has no state beyond its initial configuration, but we don't want to be
repeating that everywhere, so we'll initialise once as a singleton.
"""

import logging
import re

from airium import Airium

from html import escape
from pprint import pformat

from bleach import clean

from lib.wiki.inline import Inline
from lib.wiki.utils import get_option, trim


class Html(object):
    """
    Provide all repeatable higher-level HTML structures.
    """

    def __init__(self, settings=None):
        """
        Note that the _first_ one created will have its config used.
        """
        self.settings = settings
        self.inline = Inline()
        self.list_counter = 1

    def markup(self, text):
        """
        Apply inline processing only.
        """
        return self.inline.process(text)

    # ---------------
    # BUILDING BLOCKS
    # ---------------

    def strip_markup(self, content):
        """
        Convert to HTML and strip tags.
        """
        return clean(
            self.markup(content),
            tags=[],
            strip=True,
            strip_comments=True
        )

    # ----------------------------------------------------
    # Blocks used in CharacterBlock
    # ----------------------------------------------------

    def nav_buttons(self):
        """
        Make the buttons list.
        """
        edit_uri = self.settings.get_base_uri('edit', 'index')
        return """
            <div class="no-preview no-print">
                <div class="text-center big-space">
                  <a class="btn btn-default btn-sm" target="_blank" href="%s">
                      <i class="fa fa-pencil"></i> Edit
                  </a>
                </div>
            </div>
            """ % (edit_uri)

    def generate_grid(self, data):
        """
        For now, a simple table.
        """
        html = "<table class=\"table table-condensed\">"
        html += "<tbody>"
        for row in data:
            html += "<tr>"
            for cell in row:
                html += "<td>%s</td>" % self.markup(cell)
            html += "</tr>"
        html += "</tbody>"
        html += "</table>"
        return html


# ---------------------------
# Navigation elements
# ---------------------------

def svg_path(line: str) -> str:
    """
    Trim, and compress consecutive whitespace into a single space.
    """
    return re.sub(r'\s+', ' ', line.strip())


def font_awesome(w: int, h: int, path: str) -> Airium:
    __ = Airium()
    with __.svg(xmlns="http://www.w3.org/2000/svg", height=str(h),
                width=str(w), viewBox=f"0 0 {w*36} {h*36}"):
        __.path(d=svg_path(path))
    return __


FA_ICONS = {
    'home': font_awesome(16, 18, """
        M575.8 255.5c0 18-15 32.1-32 32.1h-32l.7 160.2c0 2.7-.2 5.4-.5
        8.1V472c0 22.1-17.9 40-40 40H456c-1.1 0-2.2 0-3.3-.1c-1.4 .1-2.8 .1-4.2
        .1H416 392c-22.1 0-40-17.9-40-40V448 384c0-17.7-14.3-32-32-32H256c-17.7
        0-32 14.3-32 32v64 24c0 22.1-17.9 40-40 40H160 128.1c-1.5
        0-3-.1-4.5-.2c-1.2 .1-2.4 .2-3.6 .2H104c-22.1 0-40-17.9-40-40V360c0-.9
        0-1.9 .1-2.8V287.6H32c-18 0-32-14-32-32.1c0-9 3-17 10-24L266.4 8c7-7
        15-8 22-8s15 2 21 7L564.8 231.5c8 7 12 15 11 24z
        """),
    'book': font_awesome(16, 18, """
        M96 0C43 0 0 43 0 96V416c0 53 43 96 96 96H384h32c17.7 0 32-14.3
        32-32s-14.3-32-32-32V384c17.7 0 32-14.3
        32-32V32c0-17.7-14.3-32-32-32H384 96zm0 384H352v64H96c-17.7
        0-32-14.3-32-32s14.3-32 32-32zm32-240c0-8.8 7.2-16 16-16H336c8.8 0 16
        7.2 16 16s-7.2 16-16 16H144c-8.8 0-16-7.2-16-16zm16 48H336c8.8 0 16 7.2
        16 16s-7.2 16-16 16H144c-8.8 0-16-7.2-16-16s7.2-16 16-16z
        """),
    'user': font_awesome(16, 14, """
        M224 256A128 128 0 1 0 224 0a128 128 0 1 0 0 256zm-45.7 48C79.8 304 0
        383.8 0 482.3C0 498.7 13.3 512 29.7 512H418.3c16.4 0 29.7-13.3
        29.7-29.7C448 383.8 368.2 304 269.7 304H178.3z
        """),
    'dark': font_awesome(16, 16, """
        M448 256c0-106-86-192-192-192V448c106 0 192-86 192-192zM0 256a256 256 0
        1 1 512 0A256 256 0 1 1 0 256z
        """),
    'full': font_awesome(16, 14, """
        M32 32C14.3 32 0 46.3 0 64v96c0 17.7 14.3 32 32 32s32-14.3
        32-32V96h64c17.7 0 32-14.3 32-32s-14.3-32-32-32H32zM64
        352c0-17.7-14.3-32-32-32s-32 14.3-32 32v96c0 17.7 14.3 32 32 32h96c17.7
        0 32-14.3 32-32s-14.3-32-32-32H64V352zM320 32c-17.7 0-32 14.3-32
        32s14.3 32 32 32h64v64c0 17.7 14.3 32 32 32s32-14.3
        32-32V64c0-17.7-14.3-32-32-32H320zM448 352c0-17.7-14.3-32-32-32s-32
        14.3-32 32v64H320c-17.7 0-32 14.3-32 32s14.3 32 32 32h96c17.7 0 32-14.3
        32-32V352z
        """),
    'menu': font_awesome(16, 14, """
        M0 96C0 78.3 14.3 64 32 64H416c17.7 0 32 14.3 32 32s-14.3 32-32
        32H32C14.3 128 0 113.7 0 96zM0 256c0-17.7 14.3-32 32-32H416c17.7 0 32
        14.3 32 32s-14.3 32-32 32H32c-17.7 0-32-14.3-32-32zM448 416c0 17.7-14.3
        32-32 32H32c-17.7 0-32-14.3-32-32s14.3-32 32-32H416c17.7 0 32 14.3 32
        32z
        """),
    'top': font_awesome(16, 12, """
        M214.6 41.4c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0
        45.3s32.8 12.5 45.3 0L160 141.2V448c0 17.7 14.3 32 32 32s32-14.3
        32-32V141.2L329.4 246.6c12.5 12.5 32.8 12.5 45.3
        0s12.5-32.8 0-45.3l-160-160z
        """),
    'edit': font_awesome(16, 16, """
        M362.7 19.3L314.3 67.7 444.3 197.7l48.4-48.4c25-25 25-65.5 0-90.5L453.3
        19.3c-25-25-65.5-25-90.5 0zm-71 71L58.6 323.5c-10.4 10.4-18 23.3-22.2
        37.4L1 481.2C-1.5 489.7 .8 498.8 7 505s15.3 8.5 23.7
        6.1l120.3-35.4c14.1-4.2 27-11.8 37.4-22.2L421.7 220.3 291.7 90.3z
        """),
}


def side_button(name: str, _id=None, _klass=None, href=None, icon=None,
                label=None) -> Airium:
    """
    Format the sidebar navigation buttons.
    """
    __ = Airium()
    button_id = _id
    button_class = 'button-unit'
    if _klass:
        button_class += ' ' + _klass
    button_icon = icon or name.lower()
    button_label = label or name
    if button_icon in FA_ICONS:
        with __.div(klass=button_class, id=button_id):
            if href:
                with __.a(klass='button-box', href=href):
                    __(FA_ICONS[button_icon])
            else:
                with __.div(klass='button-box'):
                    __(FA_ICONS[button_icon])
            __.div(klass='button-label', _t=button_label)
    else:
        logging.error('Bad side button name: ' + name)
    return __


def section_heading(nav_id, number, title_html, subtitle_html=None) -> Airium:
    """
    Format a section heading.
    """
    hx = 'h' + str(min(len(number.split('.')), 6))  # h1..h6
    __ = Airium()
    with __.hgroup(klass='section-heading'):
        with __.a(href='#' + nav_id):
            with __.div(klass='headline'):
                with __.div(klass='headline-number'):
                    getattr(__, hx)(id=nav_id, _t='§' + number + '.')
                with __.div(klass='headline-title'):
                    getattr(__, hx)(klass='balance-text', _t=title_html)
            if subtitle_html:
                __.p(klass='summary balance-text', _t=subtitle_html)
    return __


# ---------------------------
# Universal format functions.
# Mostly convenience.
# ---------------------------

def alert(content, dump_vars=None):
    """
    Show a visual error notice.
    """
    inline = Inline()
    pattern = "<div class=\"alert alert-warning\" role=\"alert\">%s</div>"
    html = pattern % inline.process(content)
    if not dump_vars:
        dump_vars = []
    html += "\n\n".join([pformat(var) for var in dump_vars])
    return html


def image(file_name, class_name=""):
    """
    Must be able to serve from redis repo.
    """
    return (
        "<div class=\"text-center %s\">"
        "<img src=\"/static/%s\" />"
        "</div>"
    ) % (
        class_name, file_name
    )


def parse_table_data(divisions, header=False):
    """
    Return data and options for a pipe-delimited table.
    Strictly speaking, this shouldn't be in the renderer.

    Divisions be like: [
        'x ! Y ! Z',
        '1 | 2 | 3'
    ]
    """
    if header:
        data = [divisions.pop(0).split('!')]
        options = ['headers']
    else:
        data = []
        options = []
    for div in divisions:
        row = [s.strip() for s in div.split(' | ')]
        data.append(row)
    return (data, options)


def generate_table(data, options=None):
    """
    Produce tables from 2D array, and 'lcr' style options.
    """
    options = options or []
    header = ''
    out = [
        "<table class=\"table table-condensed\">",
    ]
    alignments = options[0] if len(options) > 0 else ''
    if 'headers' in options:
        options.remove('headers')
        headers = data.pop(0)
        out += ["<thead>", "<tr>"]
        for _, header in enumerate(headers):
            align = alignments[_] if _ < len(alignments) else 'l'
            out += ["<th %s>%s</th>" % get_cell_formatting(align, header)]
        out += ["</tr>", "</thead>"]
    out += [
        "<tbody>"
    ]
    for row in data:
        out += ["<tr>"]
        for _, cell in enumerate(row):
            align = alignments[_] if _ < len(alignments) else 'l'
            out += ["<td %s>%s</td>" % get_cell_formatting(align, cell)]
        out += ["</tr>"]
    out += [
        "</tbody>",
        "</table>",
    ]
    return "\n".join(out)


def get_cell_formatting(align, cell):
    """
    For table_block: align is one of lrc
    """
    inline = Inline()
    if align == 'r':
        return ("class=\"text-right\"", inline.process(cell))
    elif align == 'c':
        return ("class=\"text-center\"", inline.process(cell))
    else:
        return ("class=\"text-left\"", inline.process(cell))


def space(number=1):
    """
    Vertical spacing.
    """
    return "<p class=\"text-left\">&nbsp;</p>" * number


def rule(class_name):
    """
    HR tag, with class; doffers from tag() as there is no closing tag.
    """
    return "<hr class=\"%s\" />" % class_name


def tag(tag_name, text, class_name=''):
    """
    Regular tag+class convenience function
    """
    inline = Inline()
    if text == "":
        html = "&nbsp;"
    else:
        html = inline.process(text)
    if class_name != '':
        tpl = "<%s class=\"%s\">%s</%s>"
        return tpl % (tag_name, class_name, html, tag_name)
    else:
        tpl = "<%s>%s</%s>"
        return tpl % (tag_name, html, tag_name)


def wrap(alignment_name, html, options):
    """
    Shortcut for wrapping html with alignment and width; see Wrapper and
    subclasses. Handles css_dimensions in options.
    """
    dimension = get_option(options, 1, 'dimension', None)
    if dimension == "":
        dimension = 'auto'
    if alignment_name == 'center':
        properties = ["style=\"width: %s; margin: auto;\"" % dimension]
        return trim("""
            <div %s>%s</div>
            """) % (" ".join(properties), html)
    properties = ["style=\"width: %s;\"" % dimension]
    class_property = {
        'left': 'text-left',
        'center': 'text-center',
        'right': 'pull-right',
        'indent': 'text-indent',
    }.get(alignment_name, None)
    if class_property:
        properties += ["class=\"%s\"" % class_property]
    clear = '<div class="clear"></div>' if alignment_name == 'right' else ''
    return "<div %s><span>%s</span></div>" % (" ".join(properties), html) + \
        clear


def verbatim(text):
    """
    Escape for HTML display.
    """
    return escape(text)
