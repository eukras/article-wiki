"""
Functions module 'code' for wiki.functions.

Status:
    - This is presently unused; it can be integrated when a framework for
      requiring external language libraries is decided upon.
"""

__author__ = "Nigel Chapman <nigel@chapman.id.au>"

import copy

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from lib.wiki.utils import trim
from lib.wiki.renderer import verbatim

from .base import Function


class Code(Function):
    """
    Render code samples, with syntax highlighting and line
    numbering.
    """

    examples = [
        trim("""
            CODE (python, 45) ---
            def factorial(n):
                \"\"\"e.g. 3! = 3 * 2 * 1\"\"\"
                if n == 1:
                    return 1 # end recursion
                else:
                    return n * factorial(n-1)
            ---
        """),
        ]

    def html(self, renderer):
        """
        Python's Pygments lib can handle all formatting.
        """
        opts = copy.copy(self.options)
        name = opts.pop(0)
        try:
            lexer = get_lexer_by_name(name, stripall=True)
        except Exception:
            return renderer.alert(
                "Format '%s' not recognized:" % name
                ) + verbatim(self.text)
        nums = [_ for _ in opts if _.isdigit()]
        if nums:
            start = int(nums.pop())
            formatter = HtmlFormatter(linenos=True, linenostart=start,
                                      cssclass="code")
        else:
            formatter = HtmlFormatter(linenos=False, cssclass="code")
        html = highlight(self.text, lexer, formatter)
        return html
