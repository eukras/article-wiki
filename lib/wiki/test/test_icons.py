from .context import lib  # noqa: F401

from lib.wiki.icons import Icons


def test_icons():
    icons = Icons(
        {
            "y": "check",
            "n": "cross",
            "!": "exclamation-triangle",
        }
    )
    pairs = [
        ["okay :y okay", 'okay <i class="fa fa-check"></i> okay'],
        ["okay :n okay", 'okay <i class="fa fa-cross"></i> okay'],
        ["okay :book okay", 'okay <i class="fa fa-book"></i> okay'],
        ["okay :! okay", 'okay <i class="fa fa-exclamation-triangle"></i> okay'],
        [
            "okay :exclamation-triangle okay",
            'okay <i class="fa fa-exclamation-triangle"></i> okay',
        ],
        [":y okay", '<i class="fa fa-check"></i> okay'],
        [":book okay", '<i class="fa fa-book"></i> okay'],
        ["okay :y", 'okay <i class="fa fa-check"></i>'],
        ["okay :book", 'okay <i class="fa fa-book"></i>'],
    ]
    for test, result in pairs:
        assert icons.replace(test) == result
