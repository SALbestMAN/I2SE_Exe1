# =============================================================================
# FILE OVERVIEW
# Reads plane descriptions from a CSV file and turns valid rows into Plane objects.
# =============================================================================

import csv
import math
import sys

from plane_projection.plane import Plane



# =============================================================================
# EXPLANATION
# Reads the CSV file, skips its header and empty rows, and converts each data row using _parse_plane. Invalid rows are kept as None so CSV row order remains aligned with video frames.
# Code follows below.
# =============================================================================

def load_planes(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        all_lines = list(csv.reader(f))
    data_lines = all_lines[1:]

    planes = []
    for line_number, cells in enumerate(data_lines, start=2):
        cells = [cell.strip() for cell in cells]
        if not any(cells):
            continue
        try:
            planes.append(_parse_plane(cells))
        except ValueError:
            print("[warn] CSV line %d is invalid - error frame written" % line_number, file=sys.stderr)
            planes.append(None)
    return planes



# =============================================================================
# EXPLANATION
# Validates one CSV row, converts its coordinate text to numbers, groups numbers into 3D points, and returns a Plane for either a triangle or a trapezoid.
# Code follows below.
# =============================================================================

def _parse_plane(cells):
    count = float(cells[0])
    if not math.isfinite(count) or count not in (3.0, 4.0):
        raise ValueError("the number of points must be 3 or 4")
    count = int(count)

    needed = 1 + 3 * count
    coordinate_cells = cells[1:needed]
    if len(cells) < needed or any(cell == "" for cell in coordinate_cells):
        raise ValueError("missing coordinates")
    if any(cells[needed:]):
        raise ValueError("too many values")

    coords = [float(cell) for cell in coordinate_cells]
    if not all(math.isfinite(v) for v in coords):
        raise ValueError("coordinates must be finite numbers")

    points = [tuple(coords[i:i + 3]) for i in range(0, len(coords), 3)]
    if count == 3:
        a, b, c = points
        return Plane(a, b, a, c)
    a1, b, a2, c = points
    return Plane(a1, b, a2, c)
