import json

from feedgen.feed import FeedGenerator
from typing import List
from urllib.parse import urljoin


def rss_xml(user_slug: str, articles: List[dict], base_url: str):
    """
    Generate RSS XML for a list of article metadata dicts.
    """
    feed = FeedGenerator()
    has_index = False

    for article in articles:

        title = article.get("title")
        summary = article.get("summary")
        name = article.get("author")
        email = article.get("email")

        if name:
            author = {"name": name}
            if email:
                author["email"] = email

        if article.get("slug") == "index":

            feed.id(urljoin(base_url, f"/read/{user_slug}/index"))
            feed.title(title if title != "" else "Untitled")
            feed.description(summary if summary != "" else "(no summary)")
            if name:
                feed.author(author)
            feed.logo(f"{base_url}static/site-image.png")
            feed.link(href=base_url)
            feed.link(href=f"{base_url}rss/{user_slug}.xml", rel="self")
            feed.language("en")
            feed.ttl(24 * 3600)

            has_index = True

        else:

            entry = feed.add_entry()
            article_uri = "/".join(
                [base_url, "read", article.get("user"), article.get("slug")]
            )
            entry.id(urljoin(base_url, article_uri))
            entry.title(title if title != "" else "Untitled")
            entry.description(summary if summary != "" else "(No summary)")
            entry.link(href=urljoin(base_url, article_uri))
            entry.author(name=article.get("email"), email=article.get("author"))
            entry.published(article.get("published_time"))

    if has_index:
        return feed.rss_str(pretty=True)
    else:
        return None
