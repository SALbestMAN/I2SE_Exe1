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

# --------------------------------------------------------------------------
# Plane validation and geometry
# --------------------------------------------------------------------------

EPS = 0.001
MAX_SIDE = 4096


class InvalidPlaneError(ValueError):
    """Raised when the given points do not define a valid plane."""


def _cross(u, v):
    """Calculate the cross product of two 3D vectors."""

    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0]
    )


def _vector_length(v):
    """Calculate the Euclidean length of a 3D vector."""

    return math.sqrt(sum(value * value for value in v))


def _geometry(plane):
    """Validate a plane and calculate its projection geometry."""

    ab = [
        plane.b[i] - plane.a1[i]
        for i in range(3)
    ]

    ac = [
        plane.c[i] - plane.a2[i]
        for i in range(3)
    ]

    a12 = [
        plane.a2[i] - plane.a1[i]
        for i in range(3)
    ]

    dab = math.dist(plane.a1, plane.b)
    dac = math.dist(plane.a2, plane.c)
    dbc = math.dist(plane.b, plane.c)

    d12 = _vector_length(a12)

    # Check for coincident points.
    if min(dab, dac, dbc) <= 1e-12:
        raise InvalidPlaneError("Degenerate plane: coincident points.")

    # Check the isosceles condition.
    if abs(dab - dac) >= EPS:
        raise InvalidPlaneError(
            "The two sides do not have equal lengths."
        )

    if d12 > 1e-12:

        # Check the trapezoid condition.
        if d12 > dbc + 1e-9:
            raise InvalidPlaneError(
                "Distance between a1 and a2 exceeds distance between b and c."
            )

        points = (
            plane.a1,
            plane.b,
            plane.a2,
            plane.c
        )

        # Find the three points that define the largest triangle.
        best = None

        combinations = (
            (0, 1, 2, 3),
            (0, 1, 3, 2),
            (0, 2, 3, 1),
            (1, 2, 3, 0)
        )

        for i, j, k, m in combinations:

            u = [
                points[j][t] - points[i][t]
                for t in range(3)
            ]

            v = [
                points[k][t] - points[i][t]
                for t in range(3)
            ]

            normal = _cross(u, v)
            normal_length = _vector_length(normal)

            if best is None or normal_length > best[0]:
                best = (normal_length, normal, i, m)

        normal_length, normal, i, m = best

        if normal_length <= 1e-9 * max(dab, dbc, d12) ** 2:
            raise InvalidPlaneError(
                "Degenerate plane: all four points are collinear."
            )

        # Check whether the fourth point lies on the same plane.
        offset = abs(
            sum(
                normal[t] * (points[m][t] - points[i][t])
                for t in range(3)
            )
        ) / normal_length

        if offset >= EPS:
            raise InvalidPlaneError(
                "The four points are not coplanar."
            )

    else:

        # Check that the three points are not collinear.
        normal = _cross(ab, ac)

        if _vector_length(normal) <= 1e-9 * dab * dac:
            raise InvalidPlaneError(
                "Degenerate plane: the three points are collinear."
            )

    # Calculate the output dimensions.
    rows = math.ceil(dab - 1e-9)
    cols = math.ceil(dbc - 1e-9)

    if rows > MAX_SIDE or cols > MAX_SIDE:
        raise ValueError(
            f"Plane too large ({rows}x{cols})."
        )

    # Calculate unit direction vectors.
    step1 = [value / dab for value in ab]
    step2 = [value / dac for value in ac]

    return step1, step2, rows, cols, dbc


def _check_width(d12_max):
    """Check that the projected row does not exceed the maximum width."""

    if d12_max > 2 * MAX_SIDE:
        raise ValueError(
            f"Plane too wide (row length {d12_max:.0f})."
        )


# --------------------------------------------------------------------------
# NumPy projection
# --------------------------------------------------------------------------

def _round_np(values):
    """Round values to nearest integers, with halves away from zero."""

    result = np.floor(values + 0.5)

    if values.min() < 0:
        result -= (values < 0) & (result == values + 0.5)

    return result.astype(np.int64)


def project_np(vol, plane):
    """Project a plane from the 3D volume using vectorized NumPy operations."""

    step1, step2, rows, cols, dbc = _geometry(plane)

    M = vol.data
    sx, sy, sz = vol.shape

    # Calculate the starting points of every output row.
    k = np.arange(1, rows + 1, dtype=np.float64)[:, None]

    A1 = np.array(plane.a1, dtype=np.float64) + k * np.array(step1)
    A2 = np.array(plane.a2, dtype=np.float64) + k * np.array(step2)

    # Calculate the direction and length of each row.
    vec = A2 - A1
    d12 = np.linalg.norm(vec, axis=1)

    dp = np.divide(
        vec,
        d12[:, None],
        out=np.zeros_like(vec),
        where=d12[:, None] > 1e-12
    )

    n = np.floor(d12)

    _check_width(float(n.max()))

    # Generate sample positions.
    X1 = np.arange(int(n.max()) + 1, dtype=np.float64)[None, :]

    xcol = _round_np(
        dbc / 2.0 - d12[:, None] / 2.0 + X1
    )

    valid = (
        (X1 <= n[:, None])
        & (xcol >= 0)
        & (xcol < cols)
    )

    # Calculate voxel coordinates.
    linear_index = None

    for axis, size in enumerate((sx, sy, sz)):

        coordinates = _round_np(
            A1[:, axis, None] + X1 * dp[:, axis, None]
        )

        valid &= (
            (coordinates >= 0)
            & (coordinates < size)
        )

        linear_index = (
            coordinates
            if linear_index is None
            else linear_index * size + coordinates
        )

    # Read voxel values.
    values = M.reshape(-1).take(linear_index, mode="clip")

    # Prepare the output image.
    destination = (
        np.arange(rows, dtype=np.int64)[:, None] * cols
        + xcol
    )

    destination[~valid] = rows * cols

    E = np.zeros(rows * cols + 1, dtype=M.dtype)
    E[destination] = values

    return E[:rows * cols].reshape(rows, cols)