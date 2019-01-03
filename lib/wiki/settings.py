"""
Store global document settings, and substitute into text.

A copy of the global settings should be passed to the wiki process for each new
part of the document.

By convention, settings that have significance ot the wiki are capitalised,
e.g. AUTHOR, OUTLINE, NUMBERING.
"""

import re

from html import escape
from copy import deepcopy

from lib.wiki.blocks import BlockList
from lib.wiki.geometry import split_to_dictionary


class Settings(object):
    """
    More-or-less a dict wrapper, with convenience functions.
    """

    def __init__(self, defaults=None):
        """
        Load up defaults, set globals.
        """
        assert isinstance(defaults, dict) or defaults is None

        self._ = defaults if isinstance(defaults, dict) else {}

    def copy(self):
        """
        Return a copy (usually for use a local settings).
        """
        return deepcopy(self)

    def extract(self, parts: dict):
        """
        Scan the index_part for global document settings; these parts should
        have already had DEMO blocks removed, as they can also contain settings.
        """
        if 'index' in parts:
            blocks = BlockList(parts['index']).find('CharacterBlock', '$')
            for block in blocks:
                self.read_settings_block(block.content)

    def read_settings_block(self, text):
        """
        A settings block is a CharacterBlock with the control_character
        '$'. This reads one into the current settings object.

        $ AUTHOR = Me
        $ DATE = 2017-06-12
        """
        vals = split_to_dictionary(text, prefix='$', delimiter='=')
        self._.update(vals)

    def set(self, key, value):
        """
        Set a single value.
        """
        self._[key] = value

    def update(self, values):
        """
        Set a group of values from a diictionary. This does not clear the
        values that already exist; do do that just create a new Settings
        object.
        """
        assert isinstance(values, dict)
        self._.update(values)

    def get(self, key, default=None):
        """
        Return a setting if it exists.
        """
        return self._.get(key, default)

    def format_value(self, pattern):
        """
        Replace a $[pattern] marker with self._[pattern], if exists.

        @see self.decorate()
        """

        # @TODO: Implement patterns: $[tw:eukras]

        value = pattern[2:-1]
        if value[-2:] == '++':
            # Counters: @todo: Allow actual counters? 1/a/A/i/I/g/G?
            var = value[0:-2]
            if var in self._:
                if self._[var].isdigit():
                    self._[var] = str(int(self._[var]) + 1)
                    return "%s" % (self._[var])
                else:
                    return "<del>$[%s]++</del> (Not a number!)" % var
            else:
                self._[var] = '1'
                return "%s" % (self._[var])
        else:
            if value in self._:
                return self._[value]
            else:
                return '<tt class="error">%s</tt>' % escape(value)

    def decorate(self, match):
        """
        @see self.replace()
        """
        return self.format_value(match.group(0))

    def replace(self, text):
        """
        Process $[value] markers in text.
        """
        return re.sub(r'\$\[[^\]]*\]', self.decorate, text)

    def get_base_uri(self, action, part=None):
        """
        Normal base URL for any given action.
        """
        user_slug = self.get('config:user', 'guest')
        doc_slug = self.get('config:document', 'notebook')
        if part:
            return "/%s/%s/%s/%s" % (action, user_slug, doc_slug, part)
        else:
            return "/%s/%s/%s" % (action, user_slug, doc_slug)

    def set_config(self, key, list_):
        """
        Use an un-sluggable prefix to store info that users can't set.
        """
        assert isinstance(list_, list)
        self._['config:' + key] = list_

    def get_config(self, key, alternative):
        """
        Use an un-sluggable prefix to store info that users can't set.
        """
        return self.get('config:' + key, alternative)
