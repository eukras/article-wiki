"""
Article Wiki.

Outline manager: provide ordered iteration of document parts, also store wiki
processing errors.
"""

from typing import Generator

from html import escape
from jinja2 import Environment
from slugify import slugify

from lib.wiki.blocks import BlockList, CharacterBlock, get_title_data
from lib.wiki.counters import new_counter
from lib.wiki.geometry import split_to_recursive_array
from lib.wiki.inline import Inline
from lib.wiki.utils import count_words, one_line, trim


class Outline(object):
    """
    Manage order of parts and table of contents, incl. word counts.

    self.elements = [(numbering, slug, title, title_slug, word-count), ...]

    @todo: Track target totals; show completion of each area.
    """

    def __init__(self, parts: dict, counters: list):
        """
        Create contents list, replace cross-references with placeholders.
        """

        if 'index' in parts:
            hierarchy = extract_outline(parts['index'], counters)
        else:
            hierarchy = create_outline(parts)  # <-- counters? Hmmz.

        self.elements = [
            (numbering,
             slug,
             title,
             title_slug,
             count_words(parts[slug]) if slug in parts else 0)
            for numbering, (slug, title, title_slug, summary) in hierarchy
        ]
        if 'index' in parts:
            slug, title, title_slug, _ = get_title_data(
                parts['index'], 'index')
            num_words = count_words(parts['index'])
            element = (['0'], slug, title, title_slug, num_words)
            self.elements.insert(0, element)

        self.errors = {}  # <-- store wiki errors in the outline

    def __str__(self):
        """
        Simple text representation
        """
        return "".join([
            "%s %s:%s (%s)\n" % ('.'.join(numbering), slug, title, word_count)
            for (numbering, slug, title, _, word_count) in self.elements
        ])

    def __iter__(self):
        """
        Simple iterator; note structure in compile_contents.
        """
        return iter(self.elements)

    def __len__(self):
        """
        How many parts in this outline?
        """
        return len(self.elements)

    def single_page(self):
        """
        Confirm that there is just one page that isn't index or biblio.
        """
        slugs = [slug for (_, slug, _, _, _) in self.elements]
        return all([
            len(slugs) == 1,
            # 'index' not in slugs, # <-- Allowing single-page view of index.
            'biblio' not in slugs,
        ])

    def find_title(self, match_numbering):
        """
        Lookup outline tuple by numbering
        """
        for numbering, _, title, _, _ in self.elements:
            if match_numbering == numbering:
                return title
        return None

    def find_numbering(self, part_slug, default=None):
        """
        Return the numbering for a part, by slug.
        """
        for (numbering, slug, _, _, _) in self.elements:
            if slug == part_slug:
                return numbering
        return default

    def total_word_count(self):
        """
        Do the math!
        """
        return sum([int(count) for (_, _, _, _, count) in self.elements])

    def error(self, part_slug, pattern, message):
        """
        Record an error for a document part. @unused?
        """
        if part_slug not in self.errors:
            self.errors[part_slug] = []
        self.errors[part_slug] += [(pattern, message)]
        return "<kbd class=\"wr-error\" title=\"%s\">%s</kbd>" % (
            escape(pattern), escape(message)
        )

    def html(self, edit_base_uri):
        """
        Generate a table of contents.
        """
        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
            {% if outline|length > 0 %}
            <h2>Table of Contents</h2>
            <table class="table table-of-contents table-condensed">
                <tbody>
                    {% for numbering, name, slug, title, word_count, subtotal in outline %}
                    <tr>
                        {% if slug == 'index' %}
                        <td></td>
                        <td class="word-count" colspan="{{ (max_depth * 2) - 1 }}">
                            Index.
                        </td>
                        <td class="word-count">{{ word_count }}</td>
                        {% else %}

                            {% for i in range(numbering|length - 1) %}
                        <td></td>
                            {% endfor %}

                        <td class="text-right">
                            <b>{{ numbering | join('.') }}</b>.
                        </td>

                        {% if subtotal == "0" %}
                        <td colspan="{{ (max_depth - numbering|length) * 2 + 1 }}">
                        {% else %}
                        <td colspan="{{ (max_depth - numbering|length) * 2 }}">
                        {% endif %}

                            {% if word_count == "0" %}
                            <a href="{{ edit_base_uri }}/{{ slug }}?title={{ title|urlencode }}" class="unmarked">
                                <i>[+] {{ title }}</i>
                            </a>
                            {% else %}
                            <a href="#{{ name }}" class="unmarked">
                                {{ title|safe }}
                            </a>
                            {% endif %}
                        </td>

                        <td class="word-count">
                            {% if word_count == "0" %}&mdash;{% else %}{{ word_count }}{% endif %}
                        </td>

                            {% if numbering|length > 1 or subtotal != "0" %}
                                {% if subtotal != "0" %}
                        <td class="word-count">
                            \\&nbsp;<b>{{ subtotal }}</b>
                        </td>
                                {% endif %}
                                {% for i in range(numbering|length - 2) %}
                        <td>
                        </td>
                                {% endfor %}
                            {% endif %}
                        {% endif %}
                    </tr>
                    {% endfor %}
                    <tr>
                        <td></td>
                        <td class="word-count" colspan="{{ (max_depth * 2) - 1 }}">
                            Total words.
                        </td>
                        <td class="word-count"><b>{{ total_word_count }}</b></td>
                    </tr>
                </tbody>
            </table>
            {% endif %}
            """))
        inline = Inline()
        max_depth = max([len(nums) for (nums, _, _, _, _) in self.elements])
        formatted = [(numbering,
                      anchor_name(numbering, slug),
                      slug,
                      inline.process(title),
                      '{:,d}'.format(word_count),
                      '{:,d}'.format(subtotal),
                      ) for (numbering, slug, title, total_slug, word_count, subtotal)
                     in totalize(self.elements)
                     ]
        return tpl.render(
            outline=formatted,
            max_depth=max_depth,
            edit_base_uri=edit_base_uri,
            total_word_count='{:,d}'.format(self.total_word_count())
        )

    def errors_html(self):
        """
        Render an errors summary: @todo
        """
        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
            <nav id="table-of-contents">
                {% for number, name, title, word_count in outline %}
                <div class="row">
                    <div class="lg-col-9">
                        {{ number }}.
                        <a href="#{{ name }}">
                            {{ title }}
                        </a>
                    </div>
                    <div class="lg-col-3 text-right">
                        {{ word_count }}
                    </div>
                </div>
                {% endfor %}
            </nav>
            """))
        return tpl.render(errors=self.errors)

    def html_spare_parts(self, doc_parts, edit_base_uri):
        """
        Generate a list of links to a document's parts not appearing in the
        outline.

        @todo Get headings and word count.
        """
        found = [slug for (_, slug, _, _, _) in self.elements]
        spare_parts = [
            _ for _ in list(doc_parts.keys())
            if _ not in found and _ not in ['index', 'biblio']
        ]

        env = Environment(autoescape=True)
        tpl = env.from_string(trim("""
            {% if spare_parts|length > 0 %}
            <div class="wiki-note">
                These parts  do not appear in the index's outline:
                    {% for slug in spare_parts %}
                    • <a href="{{ edit_base_uri }}/{{ slug }}">{{ slug }}</a>
                {% endfor %}
                ({{ spare_parts|length }}).
            </div>
            {% endif %}
            """))
        return tpl.render(
            spare_parts=spare_parts,
            edit_base_uri=edit_base_uri
        )


# ----------------
# Module functions
# ----------------


def default_counters():
    """
    Default to: Numerals, Lowercase Alpha, Lowercase Roman, Lowercase Greek,
    Uppercase Alpha, Uppercase Roman, Uppercase Greek.
    """
    return ['1', 'a', 'i', 'g', 'A', 'I', 'G']


def anchor_name(numbering, slug):
    """
    Create unique <a id="..."> reference for headings.
    """
    assert len(numbering) > 0
    assert isinstance(slug, str)

    number = '.'.join([str(_) for _ in numbering])
    return number + '_' + slug


def extract_title(text):
    """
    Return the first paragraph in a block of text.
    """
    return one_line(text.split("\n\n", 1)[0])


def enumerate_list(items: list, counters: list, prefix: list):
    """
    Turn a recursive list into recursively numbered items:

    i.e. ['a', ['b', ['c']], 'd', 'e'] would become:

    [([1], 'a'), ([1, 1], 'b'), ([1, 1, 1], 'c'), ([2], 'd'), ([3], 'e')]

    And be rendered as:

    1. a
    1.1. b
    1.1.1. c
    2. d
    3. e
    """
    num = new_counter(counters[0]) if len(counters) > 0 else new_counter(1)
    current = 0
    out = []
    for _ in items:
        if isinstance(_, list):
            # <-- Odd.
            out += enumerate_list(_, counters[1:], prefix + [current])
        else:
            current = next(num)
            sub_prefix = prefix + [current]
            out += [(sub_prefix, _)]
    return out


def create_outline(parts: dict):
    """
    Sort the parts by their titles/slugs.
    """
    return [([str(number + 1)], get_title_data(parts[_], _))
            for number, _ in enumerate(sorted(parts.keys()))]


def extract_outline(text: str, counters: list) -> list:
    """
    Pull back the first outline block from wiki text.

    - Chapter One
    - - Heading
    """
    for _ in BlockList(text):
        if isinstance(_, CharacterBlock) and _.control_character == "-":
            hierarchy = split_to_recursive_array(_.content, '- ')
            enumeration = enumerate_list(hierarchy, counters, [])
            outline = [(numbering, (slugify(_), _, slugify(_), ''))
                       for numbering, _ in enumeration]
            return outline
    return []


def html_heading(numbering: list,
                 title: str,
                 slug: str,
                 base_edit_uri: str) -> str:
    """
    Generate the first line of each block, including the anchor tag, and
    any navigational links.

    The numbering depth determines H1..H6.
    """
    env = Environment(autoescape=True)
    tpl = env.from_string(trim("""
        <div class="pull-right">
            <span>
                <a href="{{ base_edit_uri }}{{ slug }}">Edit</a>
            </span>
        </div>
        <{{ tag }} class="balance-text">
            <a id="{{ name }}" href="#{{ name }}">
                {{ title }}
            </a>
        </{{ tag }}>
        """))
    return tpl.render(
        base_edit_uri=base_edit_uri,
        name=anchor_name(numbering, slug),
        slug=slug,
        tag='h%d' % max(1, min(6, len(numbering))),
        title=title
    )


def iterate_parts(parts: dict) -> Generator[tuple, None, None]:
    """
    Static method: put a parts dictionary in order; mainly for export.
    """
    outline = Outline(parts, default_counters())
    for (numbering, slug, title, title_slug, _) in outline:
        if slug in parts:
            # Standardize?
            yield numbering, title, slug, parts[slug]


def replace_title(text: str, old_title: str, new_title: str) -> str:
    """
    When the title of a document part changes, it may be simpler to update the
    outline in the document's index. We'll support the case that the title runs
    to the end of its line, to avoid matching the start of other titles. There
    is still a non-zero chance of matching a stray backtick and title string in
    other text. Replace one only if there are more than one.
    """
    old = "- " + old_title
    new = "- " + new_title
    lines = []
    matched = False
    for _ in text.splitlines():
        if not matched and _.startswith("- ") and _.endswith(old):
            lines.append(_.replace(old, new))
            matched = True
        else:
            lines.append(_)
    return "\n".join(lines)


def totalize(elements: list) -> list:
    """
    Iterate from bottom to top; append subtotals to each element.
    """
    assert all([isinstance(_, tuple) for _ in elements])
    subtotals = {}  # <-- {numbering: subtotal}
    new_elements = []
    for numbering, slug, title, title_slug, count in reversed(elements):
        # Add each item to each ancestor's subtotal
        parents = list(numbering)  # <-- Copy
        while len(parents) > 1:
            parents.pop()
            parent_key = ".".join([str(_) for _ in parents])
            subtotals.setdefault(parent_key, 0)
            subtotals[parent_key] += count
        # Add any already calculated subtotal to this element's tuple.
        new_element = (numbering, slug, title, title_slug, count)  # <-- Same
        key = ".".join([str(_) for _ in numbering])
        if key in subtotals:
            new_element += (subtotals[key] + count,)  # <-- To tuple
        else:
            new_element += (0,)  # <-- To tuple
        new_elements.append(new_element)
    return list(reversed(new_elements))
