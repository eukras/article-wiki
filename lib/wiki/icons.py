import re

from lib.wiki.config import Config


class Icons(object):
    """
    Map :name: to <i class="fa fa-{{ name }}"></i>
    Use a dictionary of abbreviations to allow shorthand.
    """

    def __init__(self, aliases=None):
        """
        Construct the regexes required for regular icons as well as the
        """

        if aliases:
            self.aliases = aliases
        else:
            self.aliases = Config.fontawesome_icon_aliases

        unique_chars = "".join(set("".join(list(self.aliases.keys()))))
        title_chars = r"-a-z0-9"
        extra_chars = re.sub(title_chars, "", unique_chars)
        escaped = re.escape(extra_chars)

        patterns = [
            r"^:([-" + escaped + r"a-z0-9]+)",
            r"(?<=[\W]):([-" + escaped + r"a-z0-9]+)",
        ]

        self.regexes = []
        for pattern in patterns:
            self.regexes.append(re.compile(pattern, re.MULTILINE | re.DOTALL))

    def lookup(self, matches):
        """
        When the content is ":t" => note a shortcut.
        Otherwise use whatever icon naem is given, without the fa prefix.
        Options like fa-2x or fa-rotate are ignored.
        """
        content = matches.group(1).strip(":")
        if content in self.aliases:
            return icon_tag(self.aliases[content])
        else:
            return icon_tag(content)

    def replace(self, text):
        """
        Simple callback substitutions:
        """
        for regex in self.regexes:
            text = re.sub(regex, self.lookup, text)
        return text


# Utility functions


def expand_shorthand(name):
    """
    Not used in this function, but elsewhere where we can default to the
    Config values.
    """
    if name in Config.fontawesome_icon_aliases:
        return str(Config.fontawesome_icon_aliases[name])
    else:
        return str(name)


def icon_tag(name):
    "Create font-awesome tag"
    return '<i class="fa fa-%s"></i>' % name
