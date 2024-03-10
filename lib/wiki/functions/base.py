"""
The base Function extended by others. A function can be used in the wiki
in the structure of a Function Block.

(Function itself should not be instantiated directly; the init is for
inheritance)
"""

import hmac
import urllib.parse

from airium import Airium
from html import escape
from jinja2 import Environment

from lib.data import Data, load_env_config
from lib.wiki.inline import Inline
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

    Allow $[ADMIN_USER] in articles lists.
    """
    examples = [
        trim("""
        ARTICLES ---
        $[ADMIN_USER]/article-wiki
        ---
        """)
    ]

    def html(self, renderer):

        config = load_env_config()
        data = Data(config)
        inline = Inline()

        text = self.text.replace('$[ADMIN_USER]', data.admin_user)

        articles = []
        for line in text.splitlines():
            parts = line.split('/')
            if len(parts) == 2:
                user_slug, doc_slug = parts
                metadata = data.userDocumentMetadata_get(user_slug, doc_slug)
                if metadata:
                    articles += [metadata]

        if len(articles) == 0:
            return ""

        __ = Airium()
        with __.nav(klass='article-cards'):
            for a in articles:
                word_count = int(a.get('word_count', 0))
                details = f"{a.get('date')} &middot; {word_count:,} words"
                with __.div(klass='article-card'):
                    with __.a(href=f"/read/{a.get('user')}/{a.get('slug')}"):
                        __.div(klass="article-card-title balance-text",
                               _t=inline.process(a.get('title')))
                        __.div(klass="article-card-summary balance-text",
                               _t=inline.process(a.get('summary')))
                    __.div(klass="article-card-titles",
                           _t=details)
        return str(__)


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


class Footer(Wrapper):
    """
    Format compact end section, with a divider above
    """

    examples = [
        trim("""
            FOOTER ---
            Questions and answers
            ---
        """),
    ]

    option_list = {
    }

    def wrap(self, html):
        div = '<hr class="div-left div-solid div-10em" />\n\n'
        return wrap('footer', div + html, self.options)


class Header(Wrapper):
    """
    Format compact end section, with a divider above
    """

    examples = [
        trim("""
            HEADER ---
            Introductory comments...
            ---
        """),
    ]

    option_list = {
    }

    def wrap(self, html):
        div = '\n\n<hr class="div-left div-solid div-10em" />'
        return wrap('header', html + div, self.options)


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
