"""Add a summary of biblical references to the header of each section.

References are identified with the refspy python package.
"""

from typing import Dict, Tuple
from refspy import refspy


class References:
    def __init__(self):
        self.refspy = refspy()

    def before_section_body(self, body_text: str) -> str:
        tuples = self.refspy.find_references(body_text)
        references = [ref for _, ref in tuples if ref]
        return self.refspy.make_summary(references)

    def add_end_section(self, parts: Dict[str, str]) -> Tuple[str, str] | None:
        """
        TODO: Generate an index...
        - Combine all references.
        """
        return None
