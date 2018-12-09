"""
Plugin for 12-column grid patterns in White Room
"""

from lib.wiki.renderer import verbatim

from .base import Function


class Grid(Function):
    """
    GRID ===
    1
    ---
    2
    ===
    3
    ---
    4
    ===
    """

    def syntax(self, renderer):
        """
        GRID (format) ===
        1
        ---
        2
        ===
        3
        ---
        4
        ===

        Arguments:
        - format: "6,6" ... numbers adding up to 12, defining relative
                            column widths.
        """
        return verbatim(self.syntax.__doc__)

    def html(self, renderer):
        """Render an HTML table from CSV data and options"""
        rows = [row.strip() for row in self.text.split("===")]
        cells = [[cell.strip() for cell in row.split("---")] for row in rows]
        return renderer.generate_grid(cells)
