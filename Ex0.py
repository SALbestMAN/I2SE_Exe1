#!/usr/bin/env python3

"""
Project 2D planes from a 3D MRI volume.
The input volume is stored in NRRD format.
"""

import csv
import gzip
import math
import os
import re
import sys
import time

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np


# General project settings
EPS = 1e-3
MAX_SIDE = 2048

Point = np.ndarray


@dataclass
class Volume:
    """Store the 3D MRI data."""

    data: np.ndarray

    @property
    def shape(self):
        return self.data.shape


@dataclass
class Plane:
    """Store the points that define a plane."""

    a1: Point
    b: Point
    a2: Point
    c: Point
    line_number: int

def load_nrrd(path: str) -> Volume:
    """Load a 3D NRRD volume into a NumPy array."""

    with open(path, "rb") as file:
        content = file.read()

    # Split the NRRD header from the image data.
    separator = re.search(rb"\r?\n\r?\n", content)

    if separator is None:
        raise ValueError("Invalid NRRD file: header separator not found.")

    header_bytes = content[:separator.start()]
    raw_data = content[separator.end():]

    header = header_bytes.decode("ascii")
    lines = header.splitlines()

    if not lines[0].startswith("NRRD"):
        raise ValueError("Invalid NRRD file.")

    # Read header fields.
    fields = {}

    for line in lines[1:]:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if ":=" in line:
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    # Check volume dimensions.
    dimension = int(fields.get("dimension", 0))

    if dimension != 3:
        raise ValueError("Only 3D NRRD volumes are supported.")

    sizes = tuple(map(int, fields["sizes"].split()))

    if len(sizes) != 3:
        raise ValueError("Invalid NRRD sizes.")

    # Map NRRD types to NumPy types.
    type_map = {
        "unsigned char": np.uint8,
        "uint8": np.uint8,
        "unsigned short": np.uint16,
        "uint16": np.uint16,
        "unsigned int": np.uint32,
        "uint32": np.uint32,
    }

    nrrd_type = fields["type"].lower()

    if nrrd_type not in type_map:
        raise ValueError(f"Unsupported NRRD type: {nrrd_type}")

    dtype = np.dtype(type_map[nrrd_type])

    # Apply byte order for multi-byte values.
    endian = fields.get("endian", "little").lower()

    if dtype.itemsize > 1:
        dtype = dtype.newbyteorder(
            "<" if endian == "little" else ">"
        )

    # Decode the image data.
    encoding = fields.get("encoding", "raw").lower()

    if encoding in ("gzip", "gz"):
        raw_data = gzip.decompress(raw_data)

    if encoding in ("raw", "gzip", "gz"):
        data = np.frombuffer(raw_data, dtype=dtype)

    elif encoding in ("ascii", "text", "txt"):
        data = np.fromstring(raw_data.decode("ascii"), sep=" ", dtype=dtype)

    else:
        raise ValueError(f"Unsupported NRRD encoding: {encoding}")

    expected_size = math.prod(sizes)

    if data.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} values, but found {data.size}."
        )

    # NRRD stores the first axis as the fastest-changing axis.
    data = data.reshape(sizes, order="F")

    return Volume(data=data)

# --------------------------------------------------------------------------
# CSV -> planes
# --------------------------------------------------------------------------

@dataclass
class Plane:
    """Store the four points that define a plane."""

    a1: tuple
    b: tuple
    a2: tuple
    c: tuple


def load_planes(path):
    """Read CSV rows and convert valid rows into Plane objects."""

    planes = []

    with open(path, newline="", encoding="utf-8-sig") as file:
        rows = list(csv.reader(file))

    # Skip the CSV header.
    for line_number, row in enumerate(rows[1:], start=2):
        row = [value.strip() for value in row]

        if not any(row):
            continue

        try:
            number = float(row[0])

            if not math.isfinite(number) or number not in (3.0, 4.0):
                raise ValueError

            number = int(number)
            required_values = 1 + 3 * number

            if (
                len(row) < required_values
                or any(not value for value in row[1:required_values])
                or any(row[required_values:])
            ):
                raise ValueError

            values = [float(value) for value in row[1:required_values]]

            if not all(math.isfinite(value) for value in values):
                raise ValueError

        except (ValueError, IndexError):
            print(
                f"[warn] CSV line {line_number} is invalid - error frame written",
                file=sys.stderr
            )
            planes.append(None)
            continue

        points = [
            tuple(values[i:i + 3])
            for i in range(0, len(values), 3)
        ]

        if number == 3:
            plane = Plane(points[0], points[1], points[0], points[2])
        else:
            plane = Plane(points[0], points[1], points[2], points[3])

        planes.append(plane)

    return planes