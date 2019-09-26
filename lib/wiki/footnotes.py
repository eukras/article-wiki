"""
Construct footnotes from ^[Links] in document parts.
"""

import re

from jinja2 import Template
from sortedcontainers import SortedDict

from lib.wiki.blocks import BlockList
from lib.wiki.config import Config
from lib.wiki.counters import Numbers
from lib.wiki.geometry import split_to_array
from lib.wiki.inline import Inline
from lib.wiki.outline import Outline
from lib.wiki.utils import trim


class Footnotes(object):
    """
    Manage erm... the footnotes.
    """

    def __init__(self, parts, outline):
        """
        Matches ^[link] and

        ^ That link's corresponding footnote.

        Constructs: {part_numbering, {count: (link_text, footnote_text)}}
        """
        assert isinstance(outline, Outline)
        self.outline = outline

        assert isinstance(parts, dict)
        self.links, self.footnotes = self.collate_footnotes(parts)
        self.backlinks = SortedDict()

        self.inline = Inline()
        self.counters = {}

    def collate_footnotes(self, parts):
        """
        Make lists of the links and footnotes in each section. Add
        error notices to the outline indicating mismatches.
        """
        links = {}
        notes = {}
        for slug, text in parts.items():
            links[slug] = match_links(text)
            notes[slug] = match_footnotes(text)
            num_links = len(links[slug])
            num_notes = len(notes[slug])
            if num_notes > num_links:
                message = "More <tt>^[link]s</tt> than footnotes! (+%d)"
                diff = num_notes - num_links
                self.outline.error(slug, "", message % diff)
            if num_links > num_notes:
                message = "More footnotes than <tt>^[link]s</tt>! (+%d)"
                diff = num_links - num_notes
                self.outline.error(slug, "", message % diff)
        return (links, notes)

    def get_count(self, part_slug):
        """
        Return the footnote count character for this part:
        """
        if part_slug not in self.counters:
            self.counters[part_slug] = Numbers()
        return next(self.counters[part_slug])

    def footnote(self, pattern, part_slug, count):
        """
        Take ^[some link] and return a link to its Index line.
        Also store the back-link for when the index is generated.
        If the reference if a link, make the inline text that link.
        """
        numbering = self.outline.find_numbering(part_slug)
        number = get_number(numbering)
        nav_id = get_nav_id(numbering, count)

        link_markup, punctuation = split_pattern(pattern)

        footnote_text = ''
        if part_slug in self.footnotes:
            if count in self.footnotes[part_slug]:
                footnote_text = self.footnotes[part_slug][count]
        ref_text = self.inline.process(footnote_text)

        ref_link = '<a name="footnote_%s" href="#link_%s">%s</a>' % \
                   (nav_id, nav_id, count)

        if number not in self.backlinks:
            self.backlinks[number] = {}
        self.backlinks[number][count] = (ref_link, ref_text)

        link = trim("""
                <a name="link_%s" href="#footnote_%s">%s%s<sup>%s</sup></a>
            """) % (
            nav_id, nav_id, self.inline.process(link_markup),
            punctuation, count
        )

        return link

    def sort(self):
        """
        Put the footnotes into a settled numerical order.

        Take {section_number: {count: entry}}
        Yield (section_number, [(count, entry), ...])
        """
        for section_number in sorted(self.backlinks):
            section = self.backlinks[section_number]
            sortable = {int(_): section[_] for _ in section}  # numerical
            new_section = [(_, sortable[_]) for _ in sorted(sortable)]
            yield (section_number, new_section)

    def html(self):
        """
        From a list of backlinks.

        TODO: First letters?
        """
        assert isinstance(self.backlinks, dict)
        for _ in list(self.backlinks.items()):
            assert isinstance(_, tuple)

        html = Template("""
            <section id="footnotes">
            {% if backlinks|length < 2 %}
                {% for number, entries in backlinks %}
                    {% for count, (ref_link, ref_text) in entries %}
                <div class="indent-first-line">
                    <sup>{{ ref_link|safe }}</sup> {{ ref_text|safe }}
                </div>
                    {% endfor %}
                {% endfor %}
            {% else %}
                <h1><a href="#footnotes">Footnotes</a></h1>
                <div class="columns-x2">
                {% for number, entries in backlinks %}
                    <div class="no-widows">
                        <div><b>{{ number }}</b></div>
                    {% for count, (ref_link, ref_text) in entries %}
                        <div class="indent-first-line">
                            <sup>{{ ref_link|safe }}</sup> {{ ref_text|safe }}
                        </div>
                    {% endfor %}
                    </div>
                {% endfor %}
                </div>
            {% endif %}
            </section>
            """)

        if len(self.backlinks) == 0:
            return ""
        else:
            return html.render(
                backlinks=list(self.sort()),
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


def get_nav_id(numbering, count):
    """
    #link_nav_id is the anchor in the body
    #footnote_nav_id is the anchor in the end matter
    """
    number = get_number(numbering)
    return "%s_%s" % (number, str(count))


def match_links(text):
    """
    Collect the link tags in a block of text.
    """

    pattern = r'\^\[[^\]]+\][%s]?' % re.escape(Config.punctuation)
    return {count: _ for count, _ in zip(Numbers(), re.findall(pattern, text))}


def match_footnotes(text):
    """
    Find the footnote references in a block of text.
    """
    def join_lists(_): return [elem for sublist in _ for elem in sublist]
    footnotes = join_lists([
        split_to_array(_.content, '^', capture_characters=False)
        for _ in BlockList(text).find('CharacterBlock', '^')
    ])
    return {count: _ for count, _ in zip(Numbers(), footnotes)}


def split_pattern(pattern):
    """
    Take "^[link]!" and return the important parts.
    """
    if pattern[-1] in Config.punctuation:
        link_markup = pattern[2:-2]
        punctuation = pattern[-1]
    else:
        link_markup = pattern[2:-1]
        punctuation = ''
    return (link_markup, punctuation)
