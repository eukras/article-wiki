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

from airium import Airium

from lib.slugs import slug
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
from lib.wiki.renderer import \
    Html, \
    side_button
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
    split_options
from lib.wiki.verbatim import Verbatim


class Wiki(object):
    """
    Block-based parser for Article Wiki.
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

    def process(self, user_slug, doc_slug, parts_dict,
                fragment=False, preview=False):
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

        self.demo = Demo()
        self.backslashes = Backslashes()
        self.entities = Entities()
        self.verbatim = Verbatim()

        # Demo is first: entities(self.backslashes(verbatim(demo)))
        parts = pipe([self.entities,
                      self.backslashes,
                      self.verbatim,
                      self.demo], 'insert', parts)

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

        if 'index' in parts:
            _, title, _, summary = get_title_data(parts['index'], 'index')
            self.settings.set('TITLE', title)
            self.settings.set('SUMMARY', summary)
            html_parts['index'] = self.make_index(parts)
        else:
            self.settings.set('TITLE', '')

        for (numbering, _slug, _, _, _) in self.outline:
            if _slug in parts and _slug not in ['index', 'biblio']:
                section = self.make_section(
                    numbering, _slug, parts[_slug], fragment, preview
                )
                html_parts[_slug] = section

        # -------------------------------------
        # Replace placeholder content (as HTML)
        # -------------------------------------

        html_parts = pipe([self.cross_references,
                           self.links,
                           self.citations], 'replace', html_parts)

        html_parts = pipe([self.demo,
                           self.verbatim,
                           self.backslashes,
                           self.entities], 'replace', html_parts)

        # Add footnote HTML to each part
        footnote_parts = self.footnotes.html_parts()
        pipeline = [self.verbatim, self.backslashes, self.entities]
        footnote_html = pipe(pipeline, 'replace', footnote_parts)

        for (numbering, slug, _, _, _) in self.outline:
            footnotes = footnote_html.get(slug)
            if footnotes:
                __ = Airium()
                with __.footer():
                    __.hr(klass='div-left div-solid')
                    __(footnotes)
                html_parts[slug] += str(__)

        __ = Airium()
        with __.article():
            if not fragment:
                __(self.make_header(fragment, preview))
            __(self.make_sections(html_parts, fragment, preview))
        return str(__)

    def make_header(self, fragment, preview) -> Airium:
        """
        Create front matter with margins.
        """
        __ = Airium()
        with __.div(klass='section-group'):
            if not fragment and not preview:
                with __.div(klass='left-margin'):
                    with __.div(klass='sticky-buttons nav-buttons'):
                        __(side_button(name='Home', icon='home', href='/'))
            with __.div(klass='section-list'):
                with __.div(klass='section-item'):
                    with __.div(klass='section-content'):
                        __(self.make_title_card())
                    if not fragment and not preview:
                        with __.div(klass='right-margin'):
                            with __.div(klass='sticky-buttons option-buttons'):
                                __(side_button(name='Dark', icon='adjust',
                                               _klass='theme-button'))
                                __(side_button(name='Full', icon='expand',
                                               _klass='fullscreen-button'))
        return __

    def make_sections(self, html_parts, fragment, preview) -> Airium:
        """
        Create main body of document, with sticky navigation.
        """
        __ = Airium()
        with __.div(klass='section-group'):
            if not fragment and not preview:
                with __.div(klass='left-margin'):
                    with __.div(klass='sticky-buttons'):
                        __(side_button(name='Menu', icon='bars',
                                       _klass='navigation-button'))
            with __.div(klass='section-list'):
                if 'index' in html_parts:
                    with __.div(klass='section-item'):
                        with __.div(klass='section-content'):
                            __(html_parts['index'])
                        if not fragment and not preview:
                            with __.div(klass='right-margin'):
                                with __.div(klass='sticky-buttons'):
                                    link = self.settings.get_base_uri('edit',
                                                                      'index')
                                    __(side_button(name='Edit', icon='pencil',
                                                   href=link))
                for (numbering, _slug, _, _, _) in self.outline:
                    if _slug in html_parts and _slug not in ['index', 'biblio']:
                        with __.div(klass='section-item'):
                            with __.div(klass='section-content'):
                                __(html_parts[_slug])
                            if not fragment and not preview:
                                with __.div(klass='right-margin'):
                                    with __.div(klass='sticky-buttons'):
                                        label = '§' + '.<wbr/>'.join(numbering)
                                        link = self.settings.get_base_uri(
                                                'edit', _slug)
                                        __(side_button(name=label, icon='pencil',
                                                       href=link))

                biblio_html = self.bibliography.html()
                if biblio_html != '':
                    with __.div(klass='section-item'):
                        with __.div(klass='section-content'):
                            __(biblio_html)
                        with __.div(klass='right-margin'):
                            with __.div(klass='sticky-buttons'):
                                link = self.settings.get_base_uri('edit',
                                                                  'biblio')
                                __(side_button(name='Refs', icon='pencil',
                                               href=link))

        return __

    def make_title_card(self) -> Airium:
        """
        Format the document header.

        <header>
            <hgroup>
                <h1>
                <h2>
            <div class="addresses">
                <address>
            <div class="date">
                <time>
        """
        title = self.settings.get('TITLE', '')
        subtitle = self.settings.get('SUMMARY', '')
        author = self.settings.get('AUTHOR', '')
        email = self.settings.get('EMAIL', '')
        date_str = self.settings.get('DATE', '')
        try:
            dt = parse(date_str)
            date_yyyymmdd = dt.date().isoformat()
        except ValueError:
            date_yyyymmdd = None

        __ = Airium()
        with __.header():
            inline = Inline()
            with __.hgroup():
                if title != '':
                    __.h1(klass='balance-text', _t=inline.process(title))
                if subtitle != '':
                    __.h2(klass='balance-text', _t=inline.process(subtitle))
            if author != '' or email != '':
                with __.div(klass="author-list"):
                    with __.address():
                        __.div(_t=inline.process(author))
                        __.div(_t=inline.process(email))
            if date_str != '':
                if date_yyyymmdd is not None:
                    with __.p(klass="space", rel="date"):
                        __.time(pubdate=None, datetime=date_yyyymmdd,
                                _t=inline.process(date_str))
                else:
                    __(inline.process(date_str))
        return __

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
        data['slug'] = doc_slug if doc_slug else slug(data['title'])
        data['summary'] = self.settings.get('SUMMARY', '')
        data['license'] = self.settings.get('LICENSE', '')
        data['publish'] = self.settings.get('PUBLISH', 'YES')  # <-- Default

        data['author'] = self.settings.get('AUTHOR', '')
        data['email'] = self.settings.get('EMAIL', '')

        default = date.today().strftime("%d %b %Y")
        data['date'] = self.settings.get('DATE', default)
        utc = parse_date(data['date'], tz_name)
        data['published_time'] = format_date(utc, tz_name, DATE_FORMAT_ISO8601)

        data['todo'] = self.settings.get('TODO', '')
        data['word_count'] = self.outline.total_word_count() if self.outline else 0

        return data

    def make_index(self, parts):
        """
        Front matter: index text and table of contents (from outline)
        """
        text = parts['index']
        content, _ = split_bibliography(text)
        blocks = BlockList(content)
        title, summary = blocks.pop_titles()
        content_html = blocks.html(['0'], 'index', self.settings,
                                   fragment=True)
        if not self.outline.single_page():
            edit_base_uri = self.settings.get_base_uri('edit')
            content_html += self.outline.html(edit_base_uri)
            content_html += self.outline.html_spare_parts(
                parts, edit_base_uri
            )
        return content_html

    def make_section(self, numbering, slug, text, fragment=False,
                     preview=False):
        """
        Wrap section HTML in titles and nav.
        A fragment has no heading. A preview has a heading but no context,so no
        numbering.
        """

        content, _ = split_bibliography(text)
        blocks = BlockList(content)
        content_html = blocks.html(
            numbering, slug, self.settings, fragment, preview
        )

        __ = Airium()
        with __.section(id='.'.join(numbering) + '_' + slug,
                        klass=f"body depth-{len(numbering)}"):
            with __.div(klass='section-content'):
                __(content_html)
        return str(__)


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
        fragment = ('index' not in options)
        preview = True
        part_slug = 'index' if 'index' in options else random_slug('demo-')
        lines = pattern.splitlines()
        class_name = 'wiki-demo-wide' if 'wide' in options else 'wiki-demo'
        source = "\n".join(lines[1:-1])
        output = wiki.process(None, None, {part_slug: source}, fragment,
                              preview)

        __ = Airium()
        with __.div(klass=class_name):
            with __.div(klass='wiki-demo-input'):
                __.pre(_t=escape(source))
            with __.div(klass='wiki-demo-output'):
                __(output)
        return str(__)

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
