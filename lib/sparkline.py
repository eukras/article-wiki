from airium import Airium

PAD = 0.2

LEFT = 0 + PAD
TOP = 0 + PAD
RIGHT = 14 + PAD
BOTTOM = 2 + PAD

DEFAULT_POINTS = [(0, 0)]


class Sparkline(object):
    """
    Returns a simple SVG graph for 14 points corresponding to a two week
    period.

    points:
        a list of (x, y) points
    """

    def __init__(self, points: list):
        self.points = scale_points(
            flip_vertically(fill_zeroes(points or DEFAULT_POINTS))
        )

    def svg(self, stroke="#ddddddff", fill="#ffffff40"):
        __ = Airium()
        (cx, cy) = self.points[-1] if len(self.points) > 0 else (0, 0)
        with __.svg(
            xmlns="http://www.w3.org/2000/svg",
            width="140px",
            height="20px",
            viewBox=get_view_box(self.points),
            preserveAspectRatio="none",
        ):
            __.path(
                d=get_path(self.points, close=True), stroke="transparent", fill=fill
            )
            __.path(
                d=get_path(self.points, close=False),
                stroke=stroke,
                fill="transparent",
                **{"stroke-width": "2px", "vector-effect": "non-scaling-stroke"},
            )
            __.circle(cx=cx, cy=cy, r=PAD, fill=stroke)
        return str(__)


def fill_zeroes(points: list) -> list:
    """
    Set y to 0 for any missing values in 0..14
    """
    if len(points) == 0:
        return DEFAULT_POINTS
    y_values = {x: y for x, y in points}
    return [(x, y_values.get(x, 0)) for x in range(0, 14)]


def flip_vertically(points: list) -> list:
    """
    SVG draws from the top left, so flip the Y points.
    """
    if len(points) == 0:
        return []
    max_y = max([y for x, y in points]) + 1
    return [(x, max_y - y) for x, y in points]


def scale_points(points: list) -> list:
    """
    Scale vertical points into a 0.0 to 2.2 range, so that they form a 7:1
    ratio of width to height for a 14 day period, and so that pixels are
    consistently square when we add a dot at the end point.
    """
    max_y = max([y for x, y in points])
    ratio_y = 2 / max_y
    return [(x + PAD, (y * ratio_y) + PAD) for (x, y) in points]


def get_view_box(points: list):
    """
    Return a bounding box for the sparkline
    """
    return f"{LEFT} {TOP} {RIGHT} {BOTTOM}"


def close_path(points: list) -> list:
    """
    Assuming we have the top line of a graph, add three further points to
    enclose a space extending down to the x axis.
    """
    if len(points) == 0:
        return []
    max_y = max([y for x, y in points])
    start = points[0]
    end = points[-1]
    new_points = points[:]
    new_points.insert(0, (start[0], max_y))
    new_points.append((end[0], max_y))
    return new_points


def get_outline() -> list:
    """
    Return box that contains the 14 x 2 grid
    """
    return [(TOP, LEFT), (TOP, RIGHT), (BOTTOM, RIGHT), (BOTTOM, LEFT), (TOP, LEFT)]


def get_path(points: list, close=False):
    """
    Construct an SVG path of the form: 'M 0 0 L 1 0 L 1 1 L 0 1 L 0 0' (for a
    1x1 square). (M for move to, L for line, optional Z to close.)
    """
    if len(points) == 0:
        return f"M {LEFT} {BOTTOM} L {RIGHT} {BOTTOM}"
    new_points = close_path(points) if close else points
    svg_points = [f"{x} {y}" for (x, y) in new_points]
    svg_path = "M " + " L ".join(svg_points)
    return svg_path + " Z" if close else svg_path


def svg_sparkline(points: list):
    obj = Sparkline(points)
    return obj.svg()
