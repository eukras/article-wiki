"""
Construct an index from #Tags in document parts.
"""

from jinja2 import Template
from slugify import slugify

from lib.wiki.counters import RomanNumerals
from lib.wiki.outline import Outline
from lib.wiki.utils import one_line, trim


class Index(object):
    """
    Manage order of parts and table of contents, incl. word counts.
    @todo: Track target totals; show completion of each area.
    """

    def __init__(self, outline):
        """
        Matches '%x, #x', '#[x, y]', '#alias:tag', '#[alias: Tag, aliasing]'.
        Constructs a set of tags:

        Tags: {tag, {subtag: {number: [count]}}}
        """
        assert isinstance(outline, Outline)
        self.outline = outline

        self.tags = {}
        self.counters = {}

    def __iter__(self):
        """
        Make it easy to loop through the tags.
        """
        return iter(self.tags)

    def get_count(self, part_slug):
        """
        Return the footnote counter for this part:
        """
        if part_slug not in self.counters:
            self.counters[part_slug] = RomanNumerals()
        return next(self.counters[part_slug])

    def tag(self, alias1, tag1, subtag1, punctuation, numbering, count):
        """
        Take #Tags:Tag and return a link to its Index line.
        Also store the back-link for when the index is generated.
        """

        alias = one_line(alias1)
        tag = one_line(tag1)
        subtag = one_line(subtag1)

        number = get_number(numbering)
        nav_id = get_nav_id(tag, subtag, numbering, count)

        if tag not in self.tags:
            self.tags[tag] = {}
        if subtag not in self.tags[tag]:
            self.tags[tag][subtag] = {}
        if number not in self.tags[tag][subtag]:
            self.tags[tag][subtag][number] = []

        link = trim("""
                <a name=\"%s\" href=\"#ref_%s\">%s%s<sup>%s</sup></a>
            """) % (
                nav_id, nav_id, alias, punctuation, count
            )

        ref_link = "<a name=\"ref_%s\" href=\"#%s\">%s</a>" % \
                   (nav_id, nav_id, count)

        self.tags[tag][subtag][number] += [ref_link]
        return link

    def get_sorted_tags(self):
        """
        Put tag, subtag, number tiers into sorted order.
        """
        out_tags = []
        for tag in sorted(list(self.tags.keys()), key=str.lower):
            out_subtags = []
            for subtag in sorted(list(self.tags[tag].keys()), key=str.lower):
                out_numbers = []
                for number in sorted(self.tags[tag][subtag].keys()):
                    value = self.tags[tag][subtag][number]
                    out_numbers.append((number, value))
                out_subtags.append((subtag, out_numbers))
            out_tags.append((tag, out_subtags))
        return out_tags

    def html(self):
        """
        From a list of bibliography lines.

        TODO: First letters?
        """
        assert isinstance(self.tags, dict)

        html = Template("""
            <section id="index">
            {% if not single_page %}
                <h1><a href="#index">Index</a></h1>
            {% endif %}
            <div class="columns-x3">
            {% for tag, subtags in tags %}
                <div class="no-column-break">
                    <div class="indent-hanging">
                        {{ tag }}
                    </div>
                    {% for subtag, numbers in subtags %}
                    <div class="indent-first-line">{{ subtag }}
                        {% for number, links in numbers %}
                        <b>{{ number }}</b>
                        {{ links|join(', ') }}.
                        {% endfor %}
                    </div>
                    {% endfor %}
                </div>
            {% endfor %}
            </div>
            </section>
            """)

        if len(self.tags) == 0:
            return ""
        else:
            return html.render(
                single_page=self.outline.single_page(),
                tags=self.get_sorted_tags(),
                )


# -----------------
# Support functions
# -----------------


def get_number(numbering):
    """
    Take array of ['x', 'y', 'z'], and return 'x.y.z'.
    """
    if isinstance(numbering, list):
        return '.'.join([str(_) for _ in numbering])
    else:
        return '0'  # <-- for the index

def get_nav_id(tag, subtag, numbering, count):
    """
    #nav_id is the anchor in the body
    #ref_nav_id is the anchor in the end matter
    """
    number = get_number(numbering)
    items = [_ for _ in [slugify(tag), slugify(subtag), number, str(count)]
             if _ != '']
    return '_'.join(items)
