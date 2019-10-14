"""
Render HTML output of numerous kinds, usually with awareness of settings.

Render has no state beyond its initial configuration, but we don't want to be
repeating that everywhere, so we'll initialise once as a singleton.
"""

import locale

from html import escape
from pprint import pformat

from bleach import clean
from slugify import slugify

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

    def UNUSED____make_subheader(self, numbering, title):
        """
        call(['1', '2', '1'], 'Title')
        """
        slug = slugify(title)
        path = self.settings.get_base_uri('edit') + '/' + slug
        header_tag = 'h' + (len(numbering) + 1)  # <-- h2, h3, etc
        number = '.'.join([str(_) for _ in numbering])
        if len(number) > 0:
            prefix = number + ' &nbsp; '
            prefix_slug = number + '-'
        else:
            prefix = ''
            prefix_slug = ''
        return """
            <h%s class="show-parent balance-text" id="%s">
                <div class="no-preview no-print">
                    <div class="float-right">
                      <a class="button" target="_blank" href="%s">
                          <i class="fa fa-pencil"></i> Edit
                      </a>
                    </div>
                </div>
                <a href="#%s">%s</a>
            </h%s>
            """ % (
            header_tag,
            prefix_slug + slug, path, prefix_slug + slug,
            prefix + self.markup(title),
            header_tag
        )

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
    Produce tables from 2D array, and 'lcr$' style options.

    @todo: specify $ LOCALE = ... in settings.
    """
    options = options or []
    locale.setlocale(locale.LC_ALL, 'en_CA.UTF-8')  # For currency.
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
    For table_block: align is one of lrc$
    """
    inline = Inline()
    if align == 'r':
        return ("class=\"text-right\"", inline.process(cell))
    elif align == 'c':
        return ("class=\"text-center\"", inline.process(cell))
    elif align == '$':
        try:
            # @todo: Allow locale to be set with settings.
            value = locale.currency(float(cell), grouping=True)
        except ValueError:
            value = cell
        return ("class=\"text-right\"", value)
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


def tag(tag_name, text, class_name='', lead_sep=None, lead_tag=None):
    """
    Regular tag+class convenience function, but with the option of a leading
    title if a key-value pair is found (e.g. "~ title ~ hanging indent").
    """
    inline = Inline()
    if text == "":
        html = "&nbsp;"
    elif lead_sep and lead_tag:
        parts = text.split(lead_sep, 1)
        if len(parts) == 2:
            html = "<%s>%s</%s> &nbsp; %s" % (
                lead_tag,
                inline.process(parts[0]),
                lead_tag,
                inline.process(parts[1])
            )
        else:
            html = inline.process(text)
    else:
        html = inline.process(text)
    if class_name != '':
        return "<%s class=\"%s\">%s</%s>" % (tag_name, class_name,
                                             html, tag_name)
    else:
        return "<%s>%s</%s>" % (tag_name, html, tag_name)


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
    return "<div %s>%s</div>" % (" ".join(properties), html) + clear


def verbatim(text):
    """
    Escape for HTML display.
    """
    return escape(text)
