#!/usr/bin/python
# vim: set fileencoding: UTF8 :

"""
Library for turning Artikle Wiki docs into ebooks.
"""

from ebooklib import epub

from lib.data import Data, load_env_config
from lib.wiki.settings import Settings
from lib.wiki.wiki import Wiki


def write_epub(user_slug, doc_slug, file_path):

    # Get all the data
    config = load_env_config()
    data = Data(config)

    user = data.user_get(user_slug)  # or None
    if not user:
        raise RuntimeError("User not found: %s", user_slug)

    document = data.userDocument_get(user_slug, doc_slug)  # or Noen
    if not document:
        raise RuntimeError("Document not found: %s" % doc_slug)

    settings = Settings({
        'config:user': user_slug,
        'config:document': doc_slug,
    })
    wiki = Wiki(settings)
    xhtml = wiki.process(document)
    metadata = wiki.compile_metadata(config['TIME_ZONE'], user_slug, doc_slug)
    metadata['url'] = '/read/{:s}/{:s}'.format(user_slug, doc_slug),

    title = metadata.get('title', 'Untitled')
    author = metadata.get('author', 'Anonymous')

    chapter_file_name = doc_slug + '.xhtml'

    book = epub.EpubBook()

    # TODO: Recognise multiple chapters in when printing books.

    # set metadata
    book.set_identifier(user_slug + '+' + doc_slug)
    book.set_title(config['APP_NAME'])
    book.set_language('en')

    book.add_author(author)

    # define CSS style
    with open('static/epub.css') as f:
        style = f.read()
    global_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(global_css)

    # create chapter
    c1 = epub.EpubHtml(
        title=title,
        file_name=chapter_file_name,
        lang='en'
    )
    c1.content = xhtml
    c1.add_item(global_css)
    book.add_item(c1)

    # define Table Of Contents
    book.toc = (
        epub.Link(chapter_file_name, title, doc_slug),
        # (epub.Section(user_slug), (c1, ))
    )

    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # basic spine
    book.spine = ['nav', c1]

    # write to the file
    epub.write_epub(file_path, book, {})
