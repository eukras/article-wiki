"""
The base Function extended by others. A function can be used in the wiki
in the structure of a Function Block.

(Function itself should not be instantiated directly; the init is for
inheritance)
"""

import hmac
import json
import urllib.parse

from html import escape
from jinja2 import Environment

from lib.data import Data, load_env_config
from lib.wiki.renderer import wrap
from lib.wiki.utils import trim


class Function(object):
    """
    Base class for all function objects, which render text.
    """

    def __init__(self, options, text):
        "Standard setup."
        self.options = options  # <-- list
        self.text = text
        self.examples = []

    def docs(self):
        "Build a minimal summary from function metadata."
        return {
            'name': self.__class__.__name__,
            'description': trim(self.__doc__),
            'options': self.options,
            'examples': self.examples,
        }


class Text(Function):
    """
    Text layout with preserved whitespace and wiki formatting.
    """
    options = {}
    examples = [
        trim("""
            TEXT ---
            x x x
             x *[x] x
            ---
        """),
    ]

    def html(self, renderer):
        "Simple PRE tags"
        if 'verse' in self.options:
            return "<pre class=\"verse\">%s</pre>" % renderer.markup(self.text)
        else:
            return "<pre>%s</pre>" % renderer.markup(self.text)


class Verbatim(Function):
    """
    Show exact text in the finished document.
    """
    option_list = {}
    examples = [
        trim("""
        VERBATIM ---
        x x  x   x
         x x  x   x
          x x  x   x
        ---
        """)
    ]

    def html(self, renderer):
        "Simplest possible case..."
        return "<pre>%s</pre>" % escape(self.text)


class Articles(Function):
    """
    Take lines of the form user_slug/doc_slug.
    Present links to books, using their covers and metadata.
    """
    examples = [
        trim("""
        ARTICLES ---
        eukras/article-wiki
        ---
        """)
    ]

    def html(self, renderer):

        config = load_env_config()
        data = Data(config)

        articles = []
        for line in self.text.splitlines():
            parts = line.split('/')
            if len(parts) == 2:
                user_slug, doc_slug = parts
                metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
                if metadata:
                    articles += [metadata]

        if len(articles) == 0:
            return ""

        env = Environment(autoescape=False)
        tpl = env.from_string(trim("""
            <nav class="article-cards">
            {% for a in articles %}
                <div class="article-card">

                    <a
                        href="/read/{{ a['user'] }}/{{ a['slug'] }}"
                    >
                        <div class="article-card-title balance-text">
                            {{ a['title'] }}
                        </div>
                        <div class="article-card-summary balance-text">
                            {{ a['summary'] }}
                        </div>
                    </a>

                    {% set words = a.word_count | int %}
                    <div class="article-card-details">
                        {{ a['date'] }} &middot; {{ "{:,d}".format(words) }} words
                    </div>
                    <div class="article-card-download">
                        <a 
                            href="/epub/{{ a['user'] }}/{{ a['slug'] }}"
                        >
                            <i class="fa fa-arrow-circle-down" ></i> eBook
                        </a>
                    </div>

                </div>
            {% endfor %}
            </nav>
        """))

        return tpl.render(
            articles=articles
        )


class Wrapper(Function):
    """
    Wrappers ONLY wrap tags around rendered HTML, but otherwise look much the
    same as Functions.
    """
    pass


class Left(Wrapper):
    """
    Left align a section of text, optionally setting width.
    """

    examples = [
        trim("""
            LEFT (50%) ---
            . Big Corporation
            . Level 45
            . 156 George St
            . Sydney
            . NSW 2000
            ---
        """),
    ]

    option_list = {
        '1': "width (e.g. 5% or 5em)",
    }

    def wrap(self, html):
        "Wrap in left alignment."
        return wrap('left', html, self.options)


class Center(Wrapper):
    """
    Center align a section of text, optionally setting width.
    """

    examples = [
        trim("""
            CENTER (50%) ---
            . You are invited
            . to the wedding of
            . Jenny and Dave
            ---
        """),
    ]

    option_list = {
        '1': "width (integer; % or em)",
    }

    def wrap(self, html):
        "Wrap in center alignment."
        return wrap('center', html, self.options)


class Right(Wrapper):
    """
    Center align a section of text, optionally setting width.
    """

    examples = [
        trim("""
            RIGHT (33%) ---
            . Sender
            . Address Line
            . Locality
            . State Postcode
            ---
        """),
    ]

    option_list = {
        '1': "width (integer; % or em)",
    }

    def wrap(self, html):
        "Wrap in right alignment."
        return wrap('right', html, self.options)


class Float(Wrapper):
    """
    Center align a section of text, optionally setting width.
    """

    examples = [
        trim("""
            FLOAT (33%) ---
            . Sender
            . Address Line
            . Locality
            . State Postcode
            ---
        """),
    ]

    option_list = {
        '1': "width (integer; % or em)",
    }

    def wrap(self, html):
        "Wrap in right alignment."
        return wrap('float', html, self.options)


class Indent(Wrapper):
    """
    Indent a section of text, optionally setting widths. Indents
    are consistently about 2.3em.
    """

    examples = [
        trim("""
            INDENT (33%) ---
            . Recipient
            . Address Line
            . Locality
            . State Postcode
            ---
        """),
    ]

    option_list = {
        '1': "width (integer; % or em)",
    }

    def wrap(self, html):
        "Wrap in indentation."
        return wrap('indent', html, self.options)


class Quote(Wrapper):
    """
    Quotes are like indents, but with a smaller font size, and using blockquote
    tags.
    """

    examples = [
        trim("""
            QUOTE ---
            . Line
            : Indented line
            , Reference
            ---
        """),
    ]

    option_list = {
        '1': "width (integer; % or em)",
    }

    def wrap(self, html):
        "Wrap in indentation."
        return '<blockquote>{:s}</blockquote>'.format(html)


class Compact(Wrapper):
    """
    Make the text occupy as little space as possible. This is usually for a
    suplementary text that migt be read but probably will not.
    """

    examples = [
        trim("""
            COMPACT (2cols) ---
            lots of text lots of text lots of text lots of text lots of
            text lots of text lots of text lots of text lots of text lots
            of text lots of text lots of text lots of text lots of text
            lots of text lots of text lots of text lots of text lots of
            text lots of text lots of text lots of text lots of text lots
            of text lots of text lots of text lots of text lots of text
            ---
        """),
    ]

    option_list = {
        '1': "2cols, 3cols (optional)"
    }

    def wrap(self, html):
        """
        Just set bootstrap column options.
        """
        if '2cols' in self.options:
            columns = ' columns-x2 column-rule'
        elif '3cols' in self.options:
            columns = ' columns-x3 column-rule'
        else:
            columns = ''
        return "<div class=\"compact%s\">%s</div>" % (columns, html)


class Feature(Function):
    """
    Use /image/quote to render a string as an image overlay, suitable for
    sharing on social media.
    """

    def html(self, renderer):
        """
        Show an image/quote tag for the text.
        """
        config = load_env_config()
        key = bytes(config['APP_HASH'], 'utf-8')
        message = bytes(self.text, 'utf-8')
        checksum = hmac.new(key, message, 'sha224').hexdigest()[:16]
        encoded = urllib.parse.quote_plus(message)
        # print(json.dumps(self.text), key, checksum)
        return trim("""
            <div class="wiki-feature no-print">
                <img title="%s" src="/image/quote/%s/%s.jpg" />
            </div>
            """) % (escape(self.text), checksum, encoded)


class Box(Wrapper):
    """
    Just a simple box.
    """

    examples = [
        trim("""
            BOX ---
            lots of text lots of text lots of text lots of text lots of
            text lots of text lots of text lots of text lots of text lots
            of text lots of text lots of text lots of text lots of text
            lots of text lots of text lots of text lots of text lots of
            text lots of text lots of text lots of text lots of text lots
            of text lots of text lots of text lots of text lots of text
            ---
        """),
    ]

    option_list = {
    }

    def wrap(self, html):
        """
        Wrap inner HTML.
        """
        return "<div class=\"box-dotted\">%s</div>" % html


class Web(Wrapper):
    """
    Restrict text to appearing online only.
    """

    examples = [
        trim("""
            WEB ---
            This text will only appear in web format.
            ---
        """),
    ]

    option_list = {
    }

    def wrap(self, html):
        """
        Restrict text to appearing online only.
        """
        return "<div class=\"web-only\">%s</div>" % html


class Print(Wrapper):
    """
    Restrict text to only appearing in print.
    """

    examples = [
        trim("""
            PRINT ---
            This text will only appear in print/PDF/eBook format.
            ---
        """),
    ]

    option_list = {
    }

    def wrap(self, html):
        """
        Restrict text to only appearing in print.
        """
        return "<div class=\"print-only\">%s</div>" % html
