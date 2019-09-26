"""
Article Wiki: Epub

Generate an .ePub zipfile from 
"""

import os, re

class EPub:

    def __construct__(self):

        self.pattern = re.compile(r"\{[A-Z_]+\}")

        """
        The values {'KEY' => 'VALUE'} to be replaced in all files, when
        matching self.pattern.
        """
        self.variables = {}

        """
        The paths to copy, from the root of the source directory. 
        """
        self.manifest = [
            'Mimetype',
            ''
        ]

    def setVariables(self, dict: variables):
        self.variables = variables

    def setManifest(self, list: manifest):
        self.manifest = manifest

    def repl(self, matches):
        """
        Callback function used in self.replace(). Send an exception if any key
        is unmatched.
        """
        key = matches.group(1)
        if key in self.variables:
            return self.variables[key]
        else:
            raise LookupError("Key '{:s}' was not set as a variable.") 

    def replace(self, str: text):
        """
        Search-and-replace variables in text, calling self.repl on matches.
        """
        return self.pattern.sub(self.repl, text);

    def copy(self, str: source_dir, str: target_dir):
        """
        Directories assumed to exist and be writable; OK to die if not...
        """
        for path in manifest:
            source_path = os.path.join([source_dir, path])
            target_path = os.path.join([target_dir, path])
            new_dir = os.basedir(target_path)
            if not os.is_dir(new_dir):
                os.makedirs(new_dir, exist_ok=True)
            with open(source_path, 'r') as source:
                with open(target_path, 'w') as target:
                    target.write(self.replace(source.read()))

    def write_html_files(
            self, str: target_dir, dict: html_bodies, dict: metadata
            ):
        """
        Create the HTML files from document_html and metadata and fill out the
        manifest. Note XHTML differences, esp. absence of html entities.
        """
        for slug in html_bodies:
            html_path = os.path.join(target_dir, slug + '.html')
            with open(html_path, 'w') as target:
                html_page = self.make_html_file(
                    slug, html_bodies[slug], metadata[slug]
                    )
                target.write(html_page)

    def write_manifest_json(self, metadata):
        # write manifest
        # ...
                
    def make_html_file(self, slug, html, metadata):
        """
        Read template from templates/html, substitute metadata, convert body to
        XHTML, incl. numeric entities.
        """
        

    def zip_and_rename(self, str: epub_dir, str: book_slug):
        """
        Once the template has been filled in, create the .epub; i.e. zip and
        rename.
        """
        zip_name = compress_archive_dir(epub_dir, book_slug)
        epub_name = book_slug + '.epub' 
        os.rename(zip_name, epub_name)
        return os.path.join(epub_dir, epub_name)

    def make_epub_name(user_slug, book_slug):
        "Formats a timestamped archive name for this user_slug."
        name = "article-wiki_{:s}_{:s}_{:d}-{:d}-{:d}.zip"
        now = datetime.datetime.now()
        return name.format(user_slug, book_slug, now.year, now.month, now.day)
