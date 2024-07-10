from .context import lib  # noqa: F401

from lib.wiki.settings import Settings
from lib.wiki.utils import trim


def test_replace():
    defaults = {"default_variable": "default setting"}
    settings = Settings(defaults)
    settings.read_settings_block(
        trim(
            """
        $ variable = setting
        """
        )
    )
    out = settings.replace(
        trim(
            """
        This is a $[variable], and a $[default_variable]!
        """
        )
    )
    assert out == "This is a setting, and a default setting!"


def test_counters():
    settings = Settings()
    out = settings.replace(
        trim(
            """
        $[a++], $[a++], $[a++]
        """
        )
    )
    assert out == "1, 2, 3"


def test_global_settings():
    parts = {
        "index": trim(
            """
            My Document

            $ AUTHOR = Arthur C. Clarke

            ` Part One
            """
        ),
    }
    settings = Settings()
    settings.extract(parts)
    assert settings._ == {"AUTHOR": "Arthur C. Clarke"}


def test_multiline_authors():
    parts = {
        "index": trim(
            """
            My Document

            $ AUTHOR = Arthur C. Clarke
                     + Isaac Asimov

            ` Part One
            """
        ),
    }
    settings = Settings()
    settings.extract(parts)
    assert settings._ == {"AUTHOR": "Arthur C. Clarke + Isaac Asimov"}
