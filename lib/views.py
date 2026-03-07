from jinja2 import Environment as JinjaTemplates
from jinja2 import PackageLoader


def make_views():
    return JinjaTemplates(
        loader=PackageLoader("main", "views"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
