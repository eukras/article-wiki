"""
Plugin for TABLE blocks in Article Wiki; generate HTML from CSV

@see test_table.py
"""

import csv

from lib.wiki.utils import trim
from lib.wiki.renderer import generate_table

from .base import Function


class Table(Function):
    """
    Render simple tables with column formatting.
    """

    examples = [
        trim("""
            TABLE (crl$, headers) ---
            ID, First Name, Last Name, Salary
            123, Felicity, Masters, 160000
            7, Clive, Warner, 45000
            ---
        """),
        ]

    def html(self, renderer):
        """
        Reuse the normal table layout code.
        """
        data = list(csv.reader(self.text.splitlines()))
        return generate_table(data, self.options)
