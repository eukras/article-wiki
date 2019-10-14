"""
Plugin for DOT blocks in Article Wiki; generate as HTML containing SVG.

Status:
    - This is presently unused; a good example of how plugins can utilise 
      system services (so: easy to expand to lilypond or similar text-to-svg
      integrations). 
"""

import subprocess

from lib.wiki.functions.base import Function
from lib.wiki.renderer import alert, verbatim

# No SVG in initial conversion of ebooks.

class Dot(Function):
    """
    DOT :::
    digraph Example {
        Hello -> World
    }
    :::
    """

    acceptable_formats = [  # From `man dot`,
        # - for drawing directed graphs (default for 'digraph')
        'dot',
        # - for drawing undirected graphs (default for 'graph')
        'neato',
        'twopi',            # - for radial layouts of graphs
        'circo',            # - for circular layout of graphs
        'fdp',              # - for drawing undirected graphs
        'sfdp',             # - for drawing large undirected graphs
        'patchwork',        # - for tree maps
    ]

    def syntax(self, renderer):
        """
        DOT (arguments) ===
        digraph Example {
            Hello -> World
        }
        ===

        Arguments:
        - format (optional, one of): %s

        About DOT syntax:
        - http://www.graphviz.org/ - especially:
        - http://www.graphviz.org/pdf/dotguide.pdf
        """
        self.renderer = renderer
        return verbatim(self.syntax.__doc__ %
                        '|'.join(self.acceptable_formats))

    def html(self, renderer):
        """
        Get SVG for DOT content, embed in HTML.
        """
        if len(self.options) < 1:
            self.options = [self._guess_format(self.text)]
        if len(self.options) > 1:
            return alert(self.syntax(renderer))

        dot_format = self.options.pop()
        if dot_format == '':
            dot_format = self._guess_format(self.text)
        if dot_format not in self.acceptable_formats:
            return alert(self.syntax(renderer))

        pattern = "<div classs=\"svg-wrapper\">%s</div>"
        return pattern % self._generate_svg(dot_format, self.text)

    def _guess_format(self, dot_string):
        """
        Regular directed or undirected graphs can be guessed.
        """
        if 'digraph' in dot_string:
            return 'dot'
        else:
            return 'neato'

    def _generate_svg(self, dot_format, dot_string):
        """
        Perform the DOT system call, trimming first 6 lines; graphviz MUST be
        installed; see requirements_apt.txt; ONLY tested on *NIX.
        """
        command = [
            'dot',
            '-K',
            dot_format,
            '-T'
            'svg',
            '-Nfontname=Schoolbook',
            '-Nfontsize=11']

        file_in = dot_string.encode('utf-8')
        file_out = subprocess.run(
            command, stdout=subprocess.PIPE, input=file_in
            )
        result = file_out.stdout.decode('utf-8')
        parts = result.split('<svg', 1)
        if len(parts) == 2:
            img_tag = "<img src='data:image/svg+xml;utf8,<svg%s' />"
            html = img_tag % parts[1]
            return html

        return alert("Error generating SVG.")
