"""
Manage a simple bibliography list, of full-line records.

@todo: ibid. and op. cit.
"""


import re

from jinja2 import Template
from slugify import slugify
from sortedcontainers import SortedDict

from lib.wiki.counters import Letters, Symbols
from lib.wiki.geometry import get_words
from lib.wiki.inline import Inline, strip_markup
from lib.wiki.outline import Outline


class Bibliography(object):
    """
    Parts are a dictionary of strings; one called 'biblio' is entirely
    comprised of bibliography lines; the others have optional endmatter
    separated by a line of underscores, which is also entirely comprised of
    bibliography lines.

    @todo: Allow an option of '-' for bibliography lines in end matter, so
    they wrap?  Or '~'?
    """

    def __init__(self, parts, outline):
        """
        Create bibliography entries, and the structure for recording citations
        as they occur (These will be back-linked in the bibliography's
        citations list). The unique entry_id will be a slug of author/date,
        with an added Letters() counter for uniqueness.

                        / SortedDict
        self.entries = {entry_id: entry_text}

                                       / SortedDict
        self.citations = {entry_id: {part_number: [indexes]}}
        """
        assert isinstance(outline, Outline)
        assert isinstance(parts, dict)

        self.outline = outline
        self.entries = collate_bibliography(parts)

        self.citations = {}
        self.counters = {}

        self.inline = Inline()

    def __iter__(self):
        """
        Make it easy to loop through the bibliographies.
        """
        return iter(self.entries)

    def match(self, citation, default=None):
        """
        Return the (unique) label for the first bibliography item matching all
        words in the citation. Note that citation is assumed to be the first
        part of ((Citation, Note)) before the comma, so we're not matching page
        numbers or comments.
        """
        terms = get_words(strip_markup(citation))
        for label in self.entries:
            entry = self.entries[label]
            lowercase_entry = label.lower() + ' ' + entry.lower()
            if all([_ in lowercase_entry for _ in terms]):
                return label
        return default

    def get_count(self, part_slug):
        """
        Return the footnote counter for this part:
        """
        if part_slug not in self.counters:
            if part_slug == 'index':
                self.counters[part_slug] = Symbols()
            else:
                self.counters[part_slug] = Letters()

        return next(self.counters[part_slug])

    def citation(self, citation, note, punctuation, label, numbering, count):
        """
        Take ~[Citation 2000, p.34] and return a link to its bibiography
        entry. Also store the event for summarising in the bibiography.

        @todo http://lispp.blogspot.com/2014/01/ibid-and-op-cit.html
        ibid., op. cit., loc. cit.
        """
        number = get_number(numbering)
        nav_id = get_nav_id(label, numbering, count)

        if label not in self.citations:
            self.citations[label] = {}
        if number not in self.citations[label]:
            self.citations[label][number] = []

        # Use a '-' leader to suppress brackets.
        if citation[0] == '-':
            use_citation = citation[1:]
            bracket_open, bracket_close = '', ''
        else:
            use_citation = citation
            bracket_open, bracket_close = '(', ')'

        citation_markup = self.inline.process(use_citation)

        if note.strip() != "":
            note_markup = self.inline.process(note)
            link = "<a id=\"%s\" href=\"#ref_%s\">%s%s, %s%s%s" \
                   "<sup>%s</sup></a>" % \
                   (nav_id, nav_id, bracket_open, citation_markup, note_markup,
                    bracket_close, punctuation, count)
        else:
            link = "<a id=\"%s\" href=\"#ref_%s\">%s%s%s%s" \
                   "<sup>%s</sup></a>" % \
                   (nav_id, nav_id, bracket_open, citation_markup,
                    bracket_close, punctuation, count)

        ref_link = "<a id=\"ref_%s\" href=\"#%s\">%s</a>" % \
                   (nav_id, nav_id, count)
        self.citations[label][number] += [ref_link]

        return link

    def html(self):
        """
        From a list of bibliography lines.

        TODO: First letters?
        """
        assert isinstance(self.entries, dict)

        html = Template("""
            {% if entries|length > 0 %}
            <section class="bibliography">
            {% if not single_page %}
                <h1><a href="#bibliography">Bibliography</a></h1>
            {% endif %}
            {% for label in entries %}
                <div class="indent-hanging">
                    {{ label }} {{ entries[label] }}
                    {% if sublabel in citations %}
                        {% for number in citations[sublabel] %}
                            <b>{{ number }}</b>
                            <span class="wiki-no-select">
                                [{{ citations[sublabel][number]|join(', ') }}]
                            </span>
                        {% endfor %}
                    {% endif %}
                </div>
            {% endfor %}
            </section>
            {% endif %}
            """)

        # return pformat(self.citations)

        # if len(self.citations) == 0:
        # return ""
        # else:

        return html.render(
            single_page=self.outline.single_page(),
            entries=self.entries,
            citations=self.citations
        )


# -----------------
# Support functions
# -----------------


def get_number(numbering):
    """
    Take array of ['x', 'y', 'z']; return 'x.y.z'.
    """
    if isinstance(numbering, list):
        return '.'.join([str(_) for _ in numbering])
    else:
        return '0'


def get_nav_id(label, numbering, count):
    """
    #nav_id is the citation anchor
    #ref-nav_id is the bibliography anchor
    """
    number = get_number(numbering)
    return slugify(label) + '_' + number + '_' + str(count)


def nonempty_lines(content):
    """
    Add bibliography lines to the bibliography list.
    """
    return [_.strip() for _ in content.splitlines() if _.strip() != '']


def split_bibliography(part):
    """
    Divide text from bibliography if a block of at least three underscores
    is found.
    """
    divisions = re.split(
        "\n\n_{3,} *\n\n",
        part,
        1)  # <-- only the first split
    if len(divisions) == 2:
        return divisions
    else:
        return (part, None)


def collate_bibliography(parts):
    """
    Collate the bibliography lines into a list; order it.
    """
    lines = []
    for slug, section in parts.items():
        if slug == 'biblio':
            lines += nonempty_lines(section)
        else:
            _, biblio = split_bibliography(section)
            if biblio:
                lines += nonempty_lines(biblio)
    return create_unique_labels(lines)


def get_sentences(text):
    """
    Split a string into sentences. A sentence in quotes is still a sentence.
    """
    sentences = re.findall(r"[^\.\?\!\:]*[\.\?\!\:][\"\'\s]*", text)
    trimmed_sentences = [_.strip() for _ in sentences if _ != ""]
    return trimmed_sentences


def split_label(entry):
    """
    Take a bibliography entry and return a tuple of author-year labels, and the
    remainder of the line.
    """
    four_digits = re.compile(r'\d{4}')
    sentences = get_sentences(entry)
    head, tail = ' '.join(sentences[:1]), ' '.join(sentences[1:])
    if len(sentences) > 1:
        match_author_year = four_digits.match(sentences[1])
        if match_author_year:
            head, tail = ' '.join(sentences[:2]), ' '.join(sentences[2:])
    return head, tail


def create_unique_labels(lines):
    """
    Sort the bibliography lines into a SortedDict of author-year labels,
    ensuring author-year is unique (add Counter('a') suffixes).
    """
    collation = {}
    unique_lines = sorted(list(set(lines)))
    for entry in unique_lines:
        head, tail = split_label(entry)
        if head not in collation:
            collation[head] = []
        collation[head] += [tail]
    unique_labels = SortedDict()
    for head, tails in collation.items():
        if len(tails) == 1:
            unique_labels[head] = tails[0]
        else:
            counter = Letters()
            for tail in tails:
                if len(head) > 0:
                    unique_labels[head[:-1] + next(counter) + head[-1]] = tail
    return unique_labels
