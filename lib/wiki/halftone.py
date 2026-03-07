from typing import Tuple, Callable
from PIL.ImageOps import autocontrast

import numpy as np
import PIL.Image


def apply_halftone(image: PIL.Image.Image) -> PIL.Image.Image:
    return halftone(image, euclid_dot(spacing=7, angle=33))


def halftone(
    image: PIL.Image.Image,
    spot_fn: Callable[[int, int], float],
    auto_contrast: bool = False,
) -> PIL.Image.Image:
    updated = autocontrast(image, cutoff=10) if auto_contrast else image
    arr = array_from_pil(updated)
    # When applies to numpy arrays, the '>' comparator shows pixels above
    # a threshold white and pixels below that threshold black
    diff = arr > evaluate_2d_func(arr.shape, spot_fn)
    image_out = pil_from_array(diff)
    return image_out


def euclid_dot(spacing: int, angle: int = 0):
    """Circular dot changing to square at 50% grey."""
    pixel_divisor = 2.0 / spacing

    def fn(x: int, y: int) -> float:
        fx, fy = rotate(x * pixel_divisor, y * pixel_divisor, angle)
        # to make an ellipse multiply sin/cos
        # arguments with different multipliers
        return 0.5 - (0.25 * (np.sin(np.pi * (fx + 0.5)) + np.cos(np.pi * fy)))

    return fn


def square_dot(spacing: float, angle: float = 0):
    def fn(x, y):
        x, y = rotate(x, y, angle)
        coords = np.array([x, y])
        x, y = np.abs(((np.abs(coords) / (spacing * 0.5)) % 2) - 1)
        return 1 - (0.5 * (x + y))

    return fn


def circle_dot(spacing: float, angle: float = 0):
    def fn(x, y):
        x, y = rotate(x, y, angle)
        coords = np.array([x, y])
        coords = coords / spacing
        coords = coords % 1
        coords = coords * 2 - 1
        x, y = coords
        return 1 - np.sqrt((x * x) + (y * y)) / np.sqrt(2)

    return fn


def triangle_dot(spacing: float, angle: float = 0):
    inv_spacing = 1 / spacing

    def fn(x, y):
        x, y = rotate(x, y, angle)
        coords = np.array([x, y])
        coords = coords * inv_spacing
        coords = coords % 1
        x, y = coords
        return (x + y) * 0.5

    return fn


def line(spacing: float, angle: float = 0):
    angle %= np.pi * 0.5
    inv_spacing = 1 / spacing
    sin_inv_spacing = np.sin(angle) * inv_spacing
    cos_inv_spacing = np.cos(angle) * inv_spacing

    def fn(x, y):
        value = (sin_inv_spacing * x) + (cos_inv_spacing * y)
        return np.abs(np.sign(value) * value % np.sign(value))

    return fn


def evaluate_2d_func(img_shape, fn):
    w, h = img_shape
    xaxis = np.arange(w)
    yaxis = np.arange(h)
    result = fn(xaxis[:, None], yaxis[None, :])
    return result


def rotate(x: float, y: float, angle: float) -> Tuple[float, float]:
    """
    Rotate coordinates (x, y) by given angle.

    angle: Rotation angle in degrees
    """
    angle_rad = angle / 360 * 2 * np.pi
    sin, cos = np.sin(angle_rad), np.cos(angle_rad)
    return x * cos - y * sin, x * sin + y * cos


def transform_grid(spacing, angle):
    def fn(x, y):
        x, y = rotate(x, y, angle)
        coords = np.array([x, y])
        coords = coords / spacing
        coords = coords % 1
        return coords

    return fn


def array_from_pil(img: PIL.Image.Image) -> np.ndarray:
    return np.array(img.convert("L")) / 255


def pil_from_array(arr: np.ndarray) -> PIL.Image.Image:
    return PIL.Image.fromarray((arr * 255).astype("uint8"))


spot_functions = {
    "euclid": euclid_dot,
    "square": square_dot,
    "circle": circle_dot,
    "triangle": triangle_dot,
    "line": line,
}
