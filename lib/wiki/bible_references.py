"""
Article Wiki.

Cross References placeholders.
"""

from typing import Dict, Tuple
from airium import Airium
from html import escape
from refspy import refspy
from refspy.manager import Reference
from refspy.utils import sequential_replace_tuples

# High Voltage U+26a1; special marker. Same as placeholders.
# Should have been stripped from all wiki source texts
DELIMITER = "⚡"


class BibleReferences:
    """
    Manage internal links within a document.
    """

    def __init__(self, outline):
        """
        Create refs list for bible references.
        """
        self.refspy = refspy()
        self.refs = {}
        self.placeholders = []
        self.outline = outline

    def insert(self, parts: Dict[str, str]):
        """
        Use the placeholders object defined in init().

        Create placeholders with sequential_replace. This differs from the usual
        pattern-based replacements.
        """

        assert isinstance(parts, dict)
        assert all([isinstance(_, str) for _ in list(parts.keys())])
        assert all([isinstance(_, str) for _ in parts])

        self.refs = {
            key: self.refspy.find_references(text, include_nones=True)
            for key, text in parts.items()
        }
        safe_parts = {}
        for slug, text in parts.items():
            tuples = []
            for i, tuple in enumerate(self.refs[slug]):
                match_str, reference = tuple
                placeholder = f"{DELIMITER}ref{i}{DELIMITER}"
                self.placeholders.append((placeholder, reference))
                tuples.append((match_str, placeholder))
            safe_parts[slug] = sequential_replace_tuples(text, tuples)
        return safe_parts

    def decorate(self, match_str, reference):
        """
        Mark any errors.
        """
        if reference:
            return escape(match_str)
        else:
            return f'<kbd class="wiki-error">{escape(match_str)}</kbd>'

    def replace(self, html_parts):
        """
        Replace each @[...] with a link to that section's #id.
        """
        new_html_parts = dict()
        for slug, html in html_parts.items():
            tuples = []
            for i, tuple in enumerate(self.refs[slug]):
                if tuple:
                    match_str, reference = tuple
                    placeholder = f"{DELIMITER}ref{i}{DELIMITER}"
                    replacement = self.decorate(match_str, reference)
                    tuples.append((placeholder, replacement))
            new_html_parts[slug] = sequential_replace_tuples(html, tuples)
        return new_html_parts

    def hook_before_section_body(self, slug: str) -> Tuple[str, str]:
        references = [ref for _, ref in self.refs[slug]]
        return "References.", self.refspy.make_summary(references)

    def hook_add_end_section(self) -> Tuple[str, str]:
        refs, index = [], {}
        for slug, references in self.refs.items():
            for references in self.refs[slug]:
                for reference in references:
                    if isinstance(reference, Reference):
                        abbrev_name = self.refspy.abbrev_name(reference)
                        if abbrev_name not in index:
                            index[abbrev_name] = []
                        if slug not in index[abbrev_name]:
                            refs.append(reference)
                            index[abbrev_name].append(slug)
        if not refs:
            return "Bible References", ""
        __ = Airium()
        with __.div(klass="generated"):
            if hotspots_text := self.refspy.make_hotspots(
                refs, max_chapters=7, min_references=2
            ):
                __(f"<p class='balance-text'><b>Hotspots</b>&nbsp; {hotspots_text}</p>")
                __.hr(klass="div-left div-solid")
            for _, book_collation in self.refspy.collate(sorted(refs)):
                for book, references in book_collation:
                    with __.span():
                        __.b(_t=book.name)

                    unique_refs = {}
                    for reference in references:
                        key = self.refspy.abbrev_name(reference)
                        unique_refs[key] = reference
                    for reference in sorted(unique_refs.values()):
                        with __.span(_t=self.refspy.numbers(reference)):
                            abbrev_name = self.refspy.abbrev_name(reference)
                            sorted_slugs = sorted(
                                index[abbrev_name],
                                key=lambda slug: self.outline.find_numbering(slug),
                            )
                            for slug in sorted_slugs:
                                numbering = self.outline.find_numbering(slug)
                                number_str = ".".join([str(_) for _ in numbering])
                                anchor = number_str + "_" + str(slug)
                                __.a(
                                    _t=number_str, klass="reference", href="#" + anchor
                                )
        return "Bible References", str(__)
