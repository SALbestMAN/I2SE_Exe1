# =============================================================================
# FILE OVERVIEW
# Provides functions that convert projection data into grayscale images, center images on a shared canvas, and draw error frames.
# =============================================================================

import numpy as np
from PIL import Image, ImageDraw, ImageFont



# =============================================================================
# EXPLANATION
# Scales the values in E into 8-bit grayscale from 0 to 255, clipping them to the volume-wide range lo to hi.
# Code follows below.
# =============================================================================

def to_gray(E, lo, hi):
    scale = 255.0 / (hi - lo) if hi > lo else 0.0
    clipped = np.clip(E.astype(np.float32), lo, hi)
    return ((clipped - lo) * scale).astype(np.uint8)



# =============================================================================
# EXPLANATION
# Creates a black H-by-W canvas and places the grayscale image img in its center.
# Code follows below.
# =============================================================================

def pad_gray(img, H, W):
    h, w = img.shape
    canvas = np.zeros((H, W), dtype=np.uint8)
    top, left = (H - h) // 2, (W - w) // 2
    canvas[top:top + h, left:left + w] = img
    return canvas



# =============================================================================
# EXPLANATION
# Creates a grayscale error image with a border, diagonal cross, and labels identifying the invalid plane number.
# Code follows below.
# =============================================================================

def make_error_frame(height, width, number):
    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)
    draw.line([(0, 0), (width - 1, height - 1)], fill=110, width=2)
    draw.line([(0, height - 1), (width - 1, 0)], fill=110, width=2)
    draw.rectangle([0, 0, width - 1, height - 1], outline=255)

    label = "PLANE #%d" % number
    size = max(8, min(height // 5, int(width / (0.7 * len(label)))))
    font = ImageFont.load_default(size=size)
    draw.text((width / 2, height / 2 - 0.7 * size), "ERROR", fill=255, font=font, anchor="mm")
    draw.text((width / 2, height / 2 + 0.7 * size), label, fill=255, font=font, anchor="mm")
    return np.asarray(img)
