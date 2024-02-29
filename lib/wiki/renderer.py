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


def side_button(name: str, _id=None, _klass=None, href=None, icon=None,
                label=None) -> Airium:
    """
    Format the sidebar navigation buttons.
    """
    __ = Airium()
    button_id = _id
    button_icon = icon or name.lower()
    button_label = label or name
    button_class = 'button-unit'
    if _klass:
        button_class += ' ' + _klass
    if href:
        with __.a(klass=button_class, id=button_id, href=href):
            __.i(klass='fa fa-fw fa-' + button_icon)
            __(button_label)
    else:
        with __.button(klass=button_class, type='button'):
            __.i(klass='fa fa-fw fa-' + button_icon)
            __(button_label)
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
