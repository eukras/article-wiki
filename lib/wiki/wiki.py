"""
Article Wiki: Processor

Process document dictionaries {slug: text, ...}, corresponding to text files
in directories.

@see install/help/, or /help in a browser when the app is running.
"""

import re

from html import escape
from datetime import date, datetime
from dateutil.parser import parse
from pprint import pformat

from jinja2 import Environment
from slugify import slugify

from lib.wiki.backslashes import Backslashes
from lib.wiki.bibliography import Bibliography, split_bibliography
from lib.wiki.blocks import \
    BlockList, \
    get_title_data
from lib.wiki.citations import Citations
from lib.wiki.config import Config
from lib.wiki.cross_references import CrossReferences
from lib.wiki.entities import Entities
from lib.wiki.footnotes import Footnotes
# from lib.wiki.index import Index
from lib.wiki.inline import Inline
from lib.wiki.links import Links
from lib.wiki.outline import Outline, default_counters
from lib.wiki.placeholders import Placeholders
from lib.wiki.renderer import Html
from lib.wiki.settings import Settings
# from lib.wiki.tags import Tags
from lib.wiki.utils import \
    clean_document, \
    clean_text, \
    DATE_FORMAT_ISO8601, \
    format_date, \
    parse_date, \
    pipe, \
    random_slug, \
    split_options, \
    trim
from lib.wiki.verbatim import Verbatim


class Wiki(object):
    """
    The simple block-based Article Wiki parser, designed for academic
    writing.
    """

    __version__ = '0.1'

    def __init__(self, settings=None):
        """
        Settings hold all necessary context information.
        """
        assert isinstance(settings, Settings) or settings is None

        self.settings = settings
        self.html = Html(self.settings)

        self.id_prefix = self.settings.get(
            'config:document',
            random_slug('wiki_')  # <-- else
        )

        self.outline = None
        self.cross_references = None
        self.footnotes = None
        self.links = None
        self.index = None
        self.tags = None
        self.bibliography = None
        self.citations = None

    def process(self, parts_dict, fragment=False, preview=False):
        """
        Generate a complete HTML document from a dictionary.

        - To process a directory, supply a dictionary with no 'index' key.
        - To process a document, supply a dictionary with an index entry.
        - To process an index _only_, supply {'index': text}.
        - To process a section, supply {slug: text} when slug != 'index'.
        - To process a fragment, without a headline, supply {slug: text} with
          fragment=true (used in DEMO blocks).
        """

        if len(parts_dict) == 0:
            return ValueError("Document is empty.")

        validate_document(parts_dict, fragment)
        parts, files = clean_document(parts_dict)

        # ------------------------------------------------------
        # Add placeholders for elements not processed by the wiki
        # -------------------------------------------------------

        demo = Demo()
        backslashes = Backslashes()
        entities = Entities()
        verbatim = Verbatim()

        # Demo is first: entities(backslashes(verbatim(demo)))
        parts = pipe([entities,
                      backslashes,
                      verbatim,
                      demo], 'insert', parts)

        self.settings.extract(parts)

        # @todo:decide on file support.
        self.settings.set_config('files', files)

        # @[Cross Reference]
        self.outline = Outline(parts, default_counters())
        self.cross_references = CrossReferences(parts, self.outline)

        # ^[marker]
        # ^ Reference
        self.footnotes = Footnotes(parts, self.outline, self.id_prefix)
        self.links = Links(self.footnotes, self.id_prefix)

        # #[Topic, sub-topic]
        # self.index = Index(self.outline)
        # self.tags = Tags(self.index)

        # ~[Author 2000, p.34]
        self.bibliography = Bibliography(parts, self.outline, self.id_prefix)
        self.citations = Citations(self.bibliography)

        parts = pipe([self.cross_references,  # <-- call 'insert(parts)'
                      self.links,
                      # self.tags,
                      self.citations], 'insert', parts)

        # -------------
        # Generate HTML
        # -------------

        html_parts = {}

        # if len(parts) == 1 or fragment:
        # number = 1
        # for slug in sorted(parts):
        # section = self.make_section(
        # [str(number)], slug, parts[slug], fragment, preview
        # )
        # number = + 1
        # html_parts[slug] = section
        # else:
        if 'index' in parts:
            _, title, _, summary = get_title_data(parts['index'], 'index')
            self.settings.set('TITLE', title)
            self.settings.set('SUMMARY', summary)
            html_parts['index'] = self.make_index(parts['index'])
            if not self.outline.single_page():
                edit_base_uri = self.settings.get_base_uri('edit')
                html_parts['index'] += self.outline.html(edit_base_uri)
                html_parts['index'] += self.outline.html_spare_parts(
                    parts, edit_base_uri
                )
        else:
            self.settings.set('TITLE', '')

        for (numbering, slug, _, _, _) in self.outline:
            if slug in parts and slug not in ['index', 'biblio']:
                # print u"MAKE SECTION"
                section = self.make_section(
                    numbering, slug, parts[slug], fragment, preview
                )
                html_parts[slug] = section

        # -------------------------------------
        # Replace placeholder content (as HTML)
        # -------------------------------------

        html_parts = pipe([self.cross_references,
                           # self.tags,
                           self.links,
                           self.citations], 'replace', html_parts)

        html_parts = pipe([demo,
                           verbatim,
                           backslashes,
                           entities], 'replace', html_parts)

        html = '<article>\n'
        html += html_parts['index'] if 'index' in html_parts else ''

        # logging.error("parts: {}".format(", ".join(parts.keys())))
        # logging.error("html_parts: {}".format(", ".join(html_parts.keys())))
        # logging.error("outline: {!r}".format(self.outline.elements))

        for (numbering, slug, _, _, _) in self.outline:
            if slug in parts and slug not in ['index', 'biblio']:
                html += html_parts[slug]

        html += self.make_footer()

        html += '</article>'

        return html

    def make_footer(self):
        """
        <footer>
            <section id="prefix-footnotes">
            <section id="prefix-bibliography">
            <section id="prefix-index">
        """
        endmatter = [_ for _ in [
            self.footnotes.html(),
            self.bibliography.html(),
            # self.index.html(),
        ] if _.strip() != ""]
        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
                <footer>
                {% if endmatter|length > 0 %}
                    <hr class="div-left div-solid"/>
                    {% for html in endmatter %}
                        {{ html | safe }}
                    {% endfor %}
                {% endif %}
                </footer>
            """))
        return tpl.render(
            endmatter=endmatter,
            biblio_link=self.settings.get_base_uri('edit') + '/biblio'
        )

    def dump(self):
        """
        Diagnostics 101
        """
        print(pformat(self.outline))

    def compile_metadata(self, tz_name, user_slug, doc_slug=None):
        """
        Return just the elements we want to store in the document
        metadata cache. Self.metadata is a copy of settings made after
        processing the index part, plus other items like count_words.
        """
        data = {}

        data['user'] = user_slug
        data['title'] = self.settings.get('TITLE', '')
        data['slug'] = doc_slug if doc_slug else slugify(data['title'])
        data['summary'] = self.settings.get('SUMMARY', '')
        data['license'] = self.settings.get('LICENSE', '')
        data['publish'] = self.settings.get('PUBLISH', 'YES')  # <-- Default

        data['author'] = self.settings.get('AUTHOR', '')
        data['email'] = self.settings.get('EMAIL', '')
        data['facebook'] = self.settings.get('FACEBOOK', '')
        data['twitter'] = self.settings.get('TWITTER', '')

        default = date.today().strftime("%d %b %Y")
        data['date'] = self.settings.get('DATE', default)
        utc = parse_date(data['date'], tz_name)
        data['published_time'] = format_date(utc, tz_name, DATE_FORMAT_ISO8601)

        data['todo'] = self.settings.get('TODO', '')
        data['word_count'] = self.outline.total_word_count()

        return data

    def make_index(self, text):
        """
        Front matter preceding index text.
        Multi-author blocks are disabled for now; v.0.1.0 is SINGLE_USER.
        """
        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
        <header>

            {% if title_html != "" %}
            <hgroup>
                <h1 class="balance-text">{{ title_html|safe }}</h1>
            {% if summary != "" %}
                <h2 class="balance-text">{{ summary_html|safe }}</h2>
            {% endif %}
            </hgroup>
            {% endif %}

            {% if author != "" or email != "" %}
            <div class="author-list">
                <address>
                {% if author != "" %}
                    <div>{{ author }}</div>
                {% endif %}
                {% if email != "" %}
                    <div><a href="mailto:{{ email }}">{{ email }}</a></div>
                {% endif %}
                </address>
            </div>
            {% endif %}

            {% if facebook != "" or twitter != "" %}
            <p class="space space-between">
                {% if facebook != "" %}
                <a href="https://facebook.com/{{ facebook }}" target="_blank">
                    FB: {{ facebook }}
                </a>
                {% endif %}
                {% if twitter != "" %}
                <a href="https://twitter.com/{{ twitter }}" target="_blank">
                    TW: {{ twitter }}
                </a>
                {% endif %}
            </p>
            {% endif %}

            {% if date %}
            <p class="space" rel="date">
                {% if parsed_date != None %}
                <time pubdate datetime="{{ parsed_date }}">{{ date }}</time>
                {% else %}
                {{ date }}
                {% endif %}
            </p>
            {% endif %}

        </header>
        <section>
            {{ content_html|safe }}
        </section>
        """))
        inline = Inline()
        content, _ = split_bibliography(text)
        blocks = BlockList(content)
        title, summary = blocks.pop_titles()
        content_html = blocks.html(['0'], 'index', self.settings,
                                   fragment=True)

        date_string = inline.process(self.settings.get('DATE', ''))
        try:
            dt = parse(date_string)
            date_yyyymmdd = dt.date().isoformat()
        except ValueError:
            date_yyyymmdd = None

        # author = self.split_author()
        return tpl.render(
            title_html=inline.process(title),
            summary_html=inline.process(summary),
            author=self.settings.get('AUTHOR', ''),
            email=self.settings.get('EMAIL', ''),
            facebook=self.settings.get('FACEBOOK', ''),
            twitter=self.settings.get('TWITTER', ''),
            date=date_string,
            parsed_date=date_yyyymmdd,
            edit_link=self.settings.get_base_uri('edit') + '/index',
            content_html=content_html,
        )

    # Move to geometry?
    def split_author(self, author):
        """
        UNUSED FOR NOW. v.0.1.0 is SINGLE_USER.

        Split into authors and lines.

        $ AUTHOR = Author / Affiliation
                 + Author2 / Affiliation2

        No author should return an empty list.
        """
        inline = Inline()
        if author.strip() == '':
            return []
        else:
            return [
                [inline.process(line.strip()) for line in block.split(' / ')]
                for block in author.split(' + ')
            ]

    # Move to geometry?
    def author_cols(self, author):
        """
        Return twelve-column-grid spans based on numbers.

        @todo: Fix the hackish; better solution would find the numbers for each
        row, e.g. 5 would give 3 + 2.

        @todo: Should be solved with Flexbox now.
        """
        _ = len(author)  # list
        columns = {1: 12, 2: 6, 3: 4, 4: 6}
        return columns[_] if _ in columns else 4

    def make_section(self, numbering, slug, text, fragment=False,
                     preview=False):
        """
        Wrap section HTML in titles and nav.
        A fragment has no heading. A preview has a heading but no context,so no
        numbering.
        """
        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
        <section class="body depth-{{ depth }}">
        {% if not fragment %}
        <nav class="button-list button-list-edge no-preview no-print">
            <a class="button" href="{{ edit_link }}">
                <i class="fa fa-pencil"></i> Edit
            </a>
        </nav>
        {% endif %}
        {{ content_html|safe }}
        </section>
        """))

        content, _ = split_bibliography(text)
        blocks = BlockList(content)
        content_html = blocks.html(
            numbering, slug, self.settings, fragment, preview
        )

        return tpl.render(
            depth=len(numbering),
            edit_link=self.settings.get_base_uri('edit') + '/' + slug,
            content_html=content_html,
            fragment=fragment
        )


# ------------------------------
# Module-level utility functions
# ------------------------------

def validate_document(parts, fragment):
    """
    A valid document is a dictionary whose keys and values are all unicode
    strings (rely on clean_document to coerce). It's not too big or too small.
    """
    if not isinstance(parts, dict):
        raise ValueError("A document is a dictionary.")
    _ = len(parts)
    if _ < 1 or _ > 300:
        raise ValueError("A document can have 1-300 parts (%d found)" % _)
    if fragment and _ != 1:
        raise ValueError("Only single-part documents can be fragments.")


def get_section_nav_id(numbering, slug):
    """
    #nav_id is the section anchor
    """
    number = '.'.join([str(_) for _ in numbering])
    return number + '_' + str(slug)


def is_published(article):
    """
    An article is published if

    a) article[publish] matches YYYY-MM-DD <= today
    b) article[publish] != NO
    """
    publish = article.get('publish', "YES")  # <-- visible by default
    try:
        if datetime.strptime(publish, '%Y-%m-%d'):
            return publish <= datetime.today.strftime('%Y-%m-%d')
    except ValueError:
        pass
    return publish != "NO"


def split_published(article_list):
    "Return published and unpublished lists"
    return (
        [_ for _ in article_list if is_published(_)],
        [_ for _ in article_list if not is_published(_)]
    )


# ------------------------------
# Related class: Demo
# ------------------------------


class Demo(object):
    """
    Process DEMO blocks and their arguments.

    Located here because of interdependency with Wiki().
    """
    regex = r"DEMO\s+(\([^)]+\)\s)?\s*([%s])\2\2\s*\n.+?\n\2\2\2" % \
        re.escape(Config.delimiters)

    def __init__(self, settings=None):
        "Just a thin wrapper for Placeholders; parse options in replace()."
        self.placeholders = Placeholders(self.regex, 'demo')
        if settings:
            self.settings = settings.copy()
        else:
            self.settings = Settings()
            self.settings.set('config:user', '_')
            self.settings.set('config:document', random_slug('demo'))

    def insert(self, parts):
        "Add placeholders."
        return self.placeholders.insert(parts)

    def decorate(self, pattern, part_slug):
        """
        When we process a new demo block it needs to be assigned a unique
        id_prefix as its config:document name. Micro chance of a collision;
        maybe replace with a singleton to track random IDs in use.
        """
        self.settings.set('config:document', random_slug('demo'))

        wiki = Wiki(self.settings)
        options = match_demo_options(pattern)
        wide = "-wide" if 'wide' in options else ""
        fragment = ('index' not in options)
        part_slug = 'index' if 'index' in options else random_slug('demo-')
        lines = pattern.splitlines()
        source = "\n".join(lines[1:-1])
        output = wiki.process({part_slug: source}, fragment)

        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
            <div class="wiki-demo{{ wide }} space">
                <div class="wiki-demo-source">
                    <pre>{{ source|safe }}</pre>
                </div>
                <div class="wiki-demo-output">
                    {{ output|safe }}
                </div>
            </div>
        """))

        return tpl.render(
            wide=wide,
            source=escape(source),
            output=output
        )

    def replace(self, html_parts, decorator=None):
        "Generate demo blocks."
        if decorator:
            return self.placeholders.replace(decorator, html_parts)
        else:
            return self.placeholders.replace(self.decorate, html_parts)

# ------------------------------
# Static utility functions
# ------------------------------


def is_index_part(source):
    """
    Confirm if source text is an index page -- maybe too general? Might
    repurpose `-` for outlines within non-index pages.
    """
    settings = re.search(r'^\$ (AUTHOR|DATE) = ', source, re.M)
    contents = re.search(r'^- ', source, re.M)
    return bool(settings) or bool(contents)


def match_demo_options(pattern):
    """
    Take the matched pattern, return the options list.
    """
    function_pattern = re.compile((
        r"([A-Z]+)\s+(\([^)]+\)\s)?\s*([%s])\3\3\s*\n"
    ) % re.escape(Config.delimiters))
    match = function_pattern.match(pattern)
    if match:
        _, option_list, _ = match.groups()
        options = split_options(option_list)
    else:
        options = []
    return options


def reformat_part(slug, part):
    """
    Normalise the layout of user-entered text. Remove bibliography and Demo
    blocks, process as a Blocklist, then put them back.
    """
    if slug == 'biblio':
        return part
    else:
        content, bibliography = split_bibliography(clean_text(part))
        demo_placeholders = Demo(Settings())
        parts_sans_demo_blocks = demo_placeholders.insert({slug: content})
        blocks = BlockList(parts_sans_demo_blocks[slug])
        out_sans_demo_blocks = blocks.text()
        out_parts = demo_placeholders.replace(
            {slug: out_sans_demo_blocks},
            lambda text, slug: text
        )
        out = out_parts[slug]
        if bibliography:
            out += "\n\n\n_____\n\n" + bibliography
        return out
