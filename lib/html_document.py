"""
Generate HTML, as well as handling metadata and caching.
"""

from urllib.parse import urljoin

from pydantic_core.core_schema import IncExDictOrElseSerSchema

from jinja2 import Environment
from lib.data import Data
from lib.wiki.config import Config
from lib.wiki.wiki import Wiki


class HtmlDocument:
    def __init__(
        self, data: Data, wiki: Wiki, views: Environment, config: Config
    ) -> None:
        self.data = data
        self.wiki = wiki
        self.views = views
        self.config = config

    def generate(self, user_slug: str, doc_slug: str, base_url: str):
        """
        Cacheable page generator.
        """

        metadata = {}

        doc_parts = self.data.userDocument_get(user_slug, doc_slug) or {}

        html = self.wiki.process(
            user_slug,
            doc_slug,
            doc_parts,
            fragment=False,
            preview=False,
            show_image=bool(
                self.data.userDocumentImage_exists(user_slug, doc_slug, "title.png")
            ),
        )

        self.data.userDocumentCache_set(user_slug, doc_slug, html)

        metadata = self.wiki.compile_metadata(self.data.time_zone, user_slug, doc_slug)
        metadata["url"] = f"{base_url}/read/{user_slug}/{doc_slug}"
        self.data.userDocumentMetadata_set(user_slug, doc_slug, metadata)

        uri = f"/read/{user_slug}/{doc_slug}"
        metadata["url"] = urljoin(base_url, uri)
        author_uri = f"/read/{user_slug}"
        metadata["author_url"] = urljoin(base_url, author_uri)
        metadata["home_url"] = urljoin(base_url, "/")
        image_uri = f"/image/card/{user_slug}/{doc_slug}.jpg"
        metadata["image_url"] = urljoin(base_url, image_uri)

        template = self.views.get_template("read.html")
        page_html = template.render(
            config=self.config, metadata=metadata, content_html=html
        )

        return page_html
