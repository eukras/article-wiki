#!/usr/bin/python
# vim: set fileencoding: UTF8 :

"""
Initialise most of the library and start an interactive shell.

Usage:

    python -qi console.py
"""

import inspect

from lib.data import Data, load_env_config

from dotenv import load_dotenv, find_dotenv
from jinja2 import Environment as JinjaTemplates, PackageLoader

# Config
load_dotenv(find_dotenv())
config = load_env_config()

# Redis, Jinja
data = Data(config)
views = JinjaTemplates(loader=PackageLoader('app', 'views'))


def help(pattern=''):
    signatures = {
        name: str(inspect.signature(getattr(Data, name)))
        for name, func in Data.__dict__.items()
        if callable(func) and pattern in name
    }
    line = "{:>25s}_{:10s} {:70s}"
    for method in sorted(signatures):
        head, tail = method.rsplit('_', maxsplit=1)
        print(line.format(head, tail, signatures[method]))


print("")
print("Welcome to Article Wiki Console")
print()
print("> python -qi console.py  # <-- to run interactively")
print("")
print("help()        to show the methods of the 'data' object")
print("help('term')  to show methods containing a specific term")
print("")
