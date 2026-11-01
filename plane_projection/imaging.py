# =============================================================================
# FILE OVERVIEW
# Converts projection values into grayscale images, centers images on a shared canvas, and creates error frames.
# =============================================================================

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# =============================================================================
# EXPLANATION
# Converts each value in E into a grayscale value from 0 (black) to 255 (white). Values are first limited to the range lo through hi.
# Code follows below.
# =============================================================================
def to_gray(E, lo, hi):
    # Find the multiplier that maps the input range to the grayscale range 0–255.
    if hi > lo:
        scale = 255.0 / (hi - lo)
    else:
        # If all values are equal, use zero to avoid dividing by zero.
        scale = 0.0

    # Convert the values to decimals, then keep them between lo and hi.
    values = E.astype(np.float32)
    values = np.clip(values, lo, hi)

    # Shift the lowest value to zero, scale it, and convert it to image pixels.
    gray_values = (values - lo) * scale
    return gray_values.astype(np.uint8)


# =============================================================================
# EXPLANATION
# Creates a black image of size H by W, then copies img into its center. This makes images with different sizes fit the same video frame.
# Code follows below.
# =============================================================================
def pad_gray(img, H, W):
    image_height, image_width = img.shape

    # Create a black canvas. Each number in the array represents one grayscale pixel.
    canvas = np.zeros((H, W), dtype=np.uint8)

    # Calculate where the top-left corner of img should go to center it.
    top = (H - image_height) // 2
    left = (W - image_width) // 2

    # Copy img into the center area of the black canvas.
    canvas[
        top:top + image_height,
        left:left + image_width,
    ] = img

    return canvas


# =============================================================================
# EXPLANATION
# Creates a grayscale frame for a plane that could not be processed. The frame has a border, a cross, the word ERROR, and the plane number.
# Code follows below.
# =============================================================================
def make_error_frame(height, width, number):
    # Create a black grayscale image. Pixel values in mode L range from 0 to 255.
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)

    # Draw two diagonal lines to make a cross, then draw a white border.
    draw.line([(0, 0), (width - 1, height - 1)], fill=110, width=2)
    draw.line([(0, height - 1), (width - 1, 0)], fill=110, width=2)
    draw.rectangle([0, 0, width - 1, height - 1], outline=255)

    # Create a label such as "PLANE #3" and choose a font size that fits.
    label = "PLANE #%d" % number
    font_size = max(8, min(height // 5, int(width / (0.7 * len(label)))))
    font = ImageFont.load_default(size=font_size)

    # Draw the error message and plane number near the center.
    draw.text(
        (width / 2, height / 2 - 0.7 * font_size),
        "ERROR",
        fill=255,
        font=font,
        anchor="mm",
    )
    draw.text(
        (width / 2, height / 2 + 0.7 * font_size),
        label,
        fill=255,
        font=font,
        anchor="mm",
    )

    # Convert the image to a NumPy array, like the other image functions use.
    return np.asarray(image)