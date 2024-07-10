# Generate a bokeh background image.
# Copies the generation function in the src/bokeh.js
# Note: https://codepen.io/dudleystorey/pen/GJemEX

from jinja2 import Environment
from PIL import Image
from random import randint, uniform as randfloat, choice as randitem

from lib.wiki.utils import trim


def make_background(dimensions, color):
    """
    dimensions are (width, height)
    color is (red, green, blue) of 0..255
    """
    cover = Image.new('RGB', dimensions, color)
    # cover = draw_bokeh(cover)
    return cover


def makeBokehSvg(backgroundColor, width, height):
    """
    Generate an SVG containing fuzzy and sharp circles, in a slightly angled
    lone.
    """
    fuzzy_circles = drawCircles(
        randint(30, 40),
        sizes=[3, 3, 3, 4, 5]
    )
    sharp_circles = drawCircles(
        randint(45, 65),
        sizes=[1, 1, 1, 1, 1, 1, 1, 2, 2]
    )
    env = Environment(autoescape=False)
    tpl = env.from_string(trim("""
        <svg
            xmlns="http://www.w3.org/2000/svg"
            style="background-color: {{ backgroundColor }}"
            viewBox="0 0 {{ width }} {{ height }}"
            width="100%" height="100%"
        >
            <defs>
            <filter id="blur">
            <feGaussianBlur stdDeviation="4"></feGaussianBlur>
            </filter>
            </defs>
            {% for circle in sharp_circles %}
            {{ circle }}
            {% endfor %}
            {% for circle in fuzzy_circles %}
            {{ circle }}
            {% endfor %}
        </svg>
    """))
    return tpl.render(
        backgroundColor=backgroundColor,
        width=width,
        height=height,
        fuzzy_circles=fuzzy_circles,
        sharp_circles=sharp_circles,
    )


def drawCircles(num_points, sizes):
    y_height = randint(3, 7)
    points = diagonalPoints(num_points, y_height)

    def draw(point):
        x, y = point
        radius = randitem(sizes)
        h, s, v, opacity = randHsv()
        return drawOneCircle(x, y, radius, h, s, v, opacity)
    return [draw(p) for p in points]


def drawOneCircle(x, y, radius, h, s, v, opacity):
    randOpacity = round(randfloat(0.3, opacity), 3)
    randOpacity2 = round(randfloat(0.1, (opacity * 0.5)), 3)
    env = Environment(autoescape=False)
    if (radius < 3):
        tpl = env.from_string("""
            <circle
                r="{{ radius }}%" cx="{{ x }}%" cy="{{ y }}%"
                fill="hsla({{ h }}, {{ s }}%, 90%, {{ randOpacity }})"
            >
            </circle>
            <circle
                r="{{ radius }}%" cx="{{ x }}%" cy="{{ y }}%"
                fill="none"
                stroke="white"
                stroke-opacity="{{ randOpacity2 }}"
            >
            </circle>
        """)
    else:
        tpl = env.from_string("""
            <circle
                r="{{ radius }}%" cx="{{ x }}%" cy="{{ y }}%"
                fill="hsla({{ h }}, {{ s }}%, 90%, {{ randOpacity2 }})"
                filter="url(#blur)"
            >
            </circle>
        """)
    return tpl.render(
        x=x, y=y, radius=radius, h=h, s=s, v=v,
        randOpacity=randOpacity, randOpacity2=randOpacity2
    )


def diagonalPoints(num_points, y_height):
    # y_height is how far the diagonal reaches above or below the horizontal.
    x_delta = 100.0 / num_points
    y_delta = ((y_height * 2) / num_points)
    x, y = 0, 35 + y_height
    for _ in range(num_points):
        yield [
            randint(round(x), round(x + x_delta)) + randint(-3, 3),
            randint(round(y), round(y + y_delta)) + randint(-9, 9),
        ]
        x += x_delta
        y += y_delta


def randHsv():
    return [
        randint(0, 360),
        randint(40, 80),
        randint(20, 80),
        randfloat(0, 0.5)
    ]


if __name__ == '__main__':
    print(makeBokehSvg())
