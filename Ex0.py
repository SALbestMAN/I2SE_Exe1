#!/usr/bin/env python3
"""
Ex0.py - plane projection of a 3D volume (NRRD) into a video (MP4).

Usage:
    python Ex0.py file.nrrd file.csv file.mp4 [--fps 1]
    python Ex0.py        (no arguments -> the script looks in ITS OWN FOLDER
                          (the project folder) for the first *.nrrd and the
                          first *.csv, and saves the video there as
                          <csv name>_output.mp4)

    file.nrrd : 3D volumetric data (raw / gzip encoded NRRD)
    file.csv  : each row = "N, x1,y1,z1, x2,y2,z2, x3,y3,z3 [, x4,y4,z4]"
                N = 3 -> isosceles triangle  (a, b, c):  |dist(a,b) - dist(a,c)| < EPS
                N = 4 -> isosceles trapezoid (a1, b, a2, c):
                         |dist(a1,b) - dist(a2,c)| < EPS, dist(a1,a2) <= dist(b,c),
                         and a1->b, a2->c on one plane           (EPS = 0.001)
    file.mp4  : output video, one frame per CSV row (in the CSV order).
                A row that is not a valid plane raises InvalidPlaneError; the demo
                catches it and writes an ERROR frame (black, white cross + the text
                "ERROR / PLANE #k") - all other rows still give their correct frames.

No installation is required: the script runs with the Python standard
library only. If NumPy (and imageio) happen to be installed it uses them
automatically - the projection is then ~100x faster and the video is H.264.

Algorithm (per the assignment):
    * Dab = |a->b| (= |a->c|), Dbc = |b->c|
    * the output image E has ceil(Dab) rows (y, the loop `y < Dab`) and ceil(Dbc) columns (x)
    * row y: a1 = a' + (y+1)*v(a'->b),  a2 = a'' + (y+1)*v(a''->c)
      a1 -> a2 is sampled in unit steps, centred on the row:
      x = Dbc/2 - d12/2 + x1,  E[y][x] = M[a1 + x1*dp]   (0 if outside M)
"""
import argparse
import array
import csv
import gzip
import math
import os
import struct
import sys
import time
import zlib
from dataclasses import dataclass

# Optional accelerators (never required). EX0_PURE=1 forces the built-in mode.
try:
    if os.environ.get("EX0_PURE"):
        raise ImportError
    import numpy as np
except ImportError:
    np = None
try:
    if os.environ.get("EX0_PURE"):
        raise ImportError
    import imageio
except ImportError:
    imageio = None


# --------------------------------------------------------------------------
# NRRD reader (stdlib parser; same file works with or without NumPy)
# --------------------------------------------------------------------------
# NRRD type -> (numpy dtype code, array-module typecode)
_NRRD_TYPES = {}
for _names, _np, _arr in [
    (("uchar", "unsigned char", "uint8", "uint8_t"), "u1", "B"),
    (("signed char", "int8", "int8_t"), "i1", "b"),
    (("short", "short int", "signed short", "int16", "int16_t"), "i2", "h"),
    (("ushort", "unsigned short", "unsigned short int", "uint16", "uint16_t"), "u2", "H"),
    (("int", "signed int", "int32", "int32_t"), "i4", "i"),
    (("uint", "unsigned int", "uint32", "uint32_t"), "u4", "I"),
    (("long long", "long long int", "signed long long", "int64", "int64_t"), "i8", "q"),
    (("unsigned long long", "unsigned long long int", "uint64", "uint64_t"), "u8", "Q"),
    (("float",), "f4", "f"),
    (("double",), "f8", "d"),
]:
    for _n in _names:
        _NRRD_TYPES[_n] = (_np, _arr)


class Volume:
    """3D volume with M[x, y, z] semantics.
    data  : numpy array (np mode) or flat array.array in NRRD order (pure mode)
    shape : (sx, sy, sz)"""

    def __init__(self, data, shape):
        self.data, self.shape = data, shape
        if np is not None:
            self.vmin, self.vmax = float(data.min()), float(data.max())
        else:
            self.vmin, self.vmax = float(min(data)), float(max(data))


def _split_header(raw):
    """Header / body boundary for LF or CRLF files (earliest blank line)."""
    cands = [(raw.find(b"\n\n"), 2), (raw.find(b"\r\n\r\n"), 4)]
    cands = [(p, n) for p, n in cands if p >= 0]
    if not cands:
        raise ValueError("Invalid NRRD: header terminator not found")
    pos, size = min(cands, key=lambda c: c[0])
    return raw[:pos], raw[pos + size:]


def load_nrrd(path):
    with open(path, "rb") as f:
        raw = f.read()
    header, body = _split_header(raw)
    lines = header.decode("latin-1").splitlines()
    if not lines or not lines[0].startswith("NRRD"):
        raise ValueError("Invalid NRRD: missing magic")

    fields = {}
    for line in lines[1:]:
        if line.startswith("#") or not line.strip() or ":=" in line:
            continue
        k, sep, v = line.partition(":")
        if sep:
            fields[k.strip().lower()] = v.strip()

    if "data file" in fields or "datafile" in fields:
        raise NotImplementedError("Detached NRRD data files are not supported")
    try:
        dimension = int(fields["dimension"])
        sizes = [int(s) for s in fields["sizes"].split()]
        type_name = fields["type"].lower()
    except (KeyError, ValueError) as exc:
        raise ValueError("NRRD header has missing/invalid dimension, sizes or type") from exc
    if dimension != 3 or len(sizes) != 3 or any(s <= 0 for s in sizes):
        raise ValueError("NRRD volume must be 3D with positive sizes")
    sx, sy, sz = sizes
    if type_name not in _NRRD_TYPES:
        raise NotImplementedError("Unsupported NRRD type: " + type_name)
    np_code, arr_code = _NRRD_TYPES[type_name]
    endian = fields.get("endian", "little").lower()
    if endian not in ("little", "big"):
        raise ValueError("Invalid NRRD endian: " + endian)
    little = endian == "little"
    enc = fields.get("encoding", "raw").lower()
    if enc in ("gzip", "gz"):
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError, zlib.error) as exc:
            raise ValueError("Invalid gzip-compressed NRRD data") from exc
    elif enc != "raw":
        raise NotImplementedError("Unsupported NRRD encoding: " + enc)

    count = sx * sy * sz
    expected = count * struct.calcsize(arr_code)
    if len(body) < expected:
        raise ValueError("NRRD data is truncated: expected %d bytes, got %d" % (expected, len(body)))
    body = body[:expected]
    if np is not None:
        dt = np.dtype(np_code).newbyteorder("<" if little else ">")
        a = np.frombuffer(body, dtype=dt, count=count)
        # NRRD: first axis varies fastest -> reshape reversed, transpose to [x,y,z]
        return Volume(np.ascontiguousarray(a.reshape(sz, sy, sx).transpose(2, 1, 0)), (sx, sy, sz))
    a = array.array(arr_code)
    a.frombytes(body)
    if little != (sys.byteorder == "little"):
        a.byteswap()
    return Volume(a, (sx, sy, sz))   # flat, index = x + sx*(y + sy*z)

# --------------------------------------------------------------------------
# CSV -> planes
# --------------------------------------------------------------------------
@dataclass
class Plane:
    a1: tuple  # start of the first side  (a  or a')
    b: tuple   # end of the first side
    a2: tuple  # start of the second side (a  or a'')
    c: tuple   # end of the second side


def load_planes(path):
    """One entry per CSV data row: a Plane, or None for an invalid row."""
    planes = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    for ln, row in enumerate(rows[1:], start=2):  # skip header
        row = [r.strip() for r in row]
        if not any(row):
            continue
        try:
            nv = float(row[0])
            if not math.isfinite(nv) or nv not in (3.0, 4.0):
                raise ValueError
            n = int(nv)
            need = 1 + 3 * n
            if len(row) < need or any(not r for r in row[1:need]) or any(row[need:]):   # missing / extra values
                raise ValueError
            vals = [float(r) for r in row[1:need]]
            if not all(math.isfinite(v) for v in vals):   # rejects NaN / inf
                raise ValueError
        except (ValueError, IndexError):
            print("[warn] CSV line %d is invalid - error frame written" % ln, file=sys.stderr)
            planes.append(None)   # keep one video frame per CSV row
            continue
        p = [tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)]
        planes.append(Plane(p[0], p[1], p[0], p[2]) if n == 3 else Plane(p[0], p[1], p[2], p[3]))
    return planes

# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------
MAX_SIDE = 4096     # largest plane side accepted (volumes are < 1024 per axis)


def round_nearest(v):
    """Nearest integer, exact halves away from zero (same rule in both modes)."""
    return int(math.floor(v + 0.5)) if v >= 0 else int(math.ceil(v - 0.5))


def _round_np(a):
    """Vectorised round_nearest (halves away from zero)."""
    r = np.floor(a + 0.5)
    if a.min() < 0:                                  # only negative exact halves differ
        r -= (a < 0) & (r == a + 0.5)
    return r.astype(np.int64)


EPS = 0.001      # tolerance given by the instructor (Q&A 1: "EPS can be assumed to be 0.001")


class InvalidPlaneError(ValueError):
    """The point set is not a valid plane according to the instructor's Q&A rules."""


def _geometry(pl):
    """Validate the plane (instructor Q&A) and return the per-row steps and the image size.

    Valid plane (EPS = 0.001):
      * |dist(a1,b) - dist(a2,c)| < EPS                      (3 points: a1 = a2 = a)
      * dist(a1,a2) <= dist(b,c)                             (4 points)
      * a1->b and a2->c lie on one plane                     (4th point within EPS of the plane of the other three)
    Anything else raises InvalidPlaneError. Every row advances by exactly one unit vector
    (a1 = a1 + v(ab), a2 = a2 + v(ac)), as in the assignment. The loop `y < Dab` runs
    ceil(Dab) times -> rows = ceil(Dab); cols = ceil(Dbc)."""
    ab = [pl.b[i] - pl.a1[i] for i in range(3)]
    ac = [pl.c[i] - pl.a2[i] for i in range(3)]
    a12 = [pl.a2[i] - pl.a1[i] for i in range(3)]
    dab, dac, dbc = math.dist(pl.a1, pl.b), math.dist(pl.a2, pl.c), math.dist(pl.b, pl.c)
    d12 = math.sqrt(sum(t * t for t in a12))
    if min(dab, dac, dbc) <= 1e-12:
        raise InvalidPlaneError("degenerate plane (coincident points)")
    if abs(dab - dac) >= EPS:
        raise InvalidPlaneError("|dist(a1,b) - dist(a2,c)| = %.4f is not < EPS (%g): not isosceles"
                                % (abs(dab - dac), EPS))
    cross = lambda u, v: (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    if d12 > 1e-12:                                      # 4 distinct start points (trapezoid)
        if d12 > dbc + 1e-9:
            raise InvalidPlaneError("dist(a1,a2) = %.4f exceeds dist(b,c) = %.4f" % (d12, dbc))
        # The plane is defined by the best-conditioned triple of the 4 points (largest triangle area),
        # NOT necessarily (a1,b,a2): a2 may lie on the segment a1->b and the set is still a valid plane.
        pts = (pl.a1, pl.b, pl.a2, pl.c)
        best = None
        for i, j, k, m in ((0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 3, 1), (1, 2, 3, 0)):
            u = [pts[j][t] - pts[i][t] for t in range(3)]
            v = [pts[k][t] - pts[i][t] for t in range(3)]
            n = cross(u, v)
            nl = math.sqrt(sum(t * t for t in n))
            if best is None or nl > best[0]:
                best = (nl, n, i, m)
        nl, n, i, m = best
        if nl <= 1e-9 * max(dab, dbc, d12) ** 2:
            raise InvalidPlaneError("degenerate plane (all 4 points are collinear)")
        off = abs(sum(n[t] * (pts[m][t] - pts[i][t]) for t in range(3))) / nl
        if off >= EPS:
            raise InvalidPlaneError("the 4 points are not on one plane (one point is %.4f off the plane of the other three)" % off)
    else:                                                # triangle
        n = cross(ab, ac)
        if math.sqrt(sum(t * t for t in n)) <= 1e-9 * dab * dac:
            raise InvalidPlaneError("degenerate plane (a, b, c are collinear)")
    rows, cols = math.ceil(dab - 1e-9), math.ceil(dbc - 1e-9)
    if rows > MAX_SIDE or cols > MAX_SIDE:
        raise ValueError("Plane too large (%dx%d, limit %d)" % (rows, cols, MAX_SIDE))
    step1 = [t / dab for t in ab]                        # unit vectors v(a1,b), v(a2,c)
    step2 = [t / dac for t in ac]
    return step1, step2, rows, cols, dbc


def _check_width(d12_max):
    if d12_max > 2 * MAX_SIDE:
        raise ValueError("Plane too wide (row length %.0f)" % d12_max)

    
    def project_np(vol, pl):
    """Vectorised projection (no Python loops over pixels). Returns (rows, cols) ndarray.
    Row y: a1 = a' + (y+1)*step1, a2 = a'' + (y+1)*step2, d12 = |a1a2|,
    samples x1 = 0..floor(d12) at a1 + x1*dp, written to column round(Dbc/2 - d12/2 + x1) (Dbc = exact |bc|, as in the assignment)."""
    step1, step2, rows, cols, dbc = _geometry(pl)
    M = vol.data
    sx, sy, sz = vol.shape
    k = np.arange(1, rows + 1, dtype=np.float64)[:, None]
    A1 = np.array(pl.a1, dtype=np.float64) + k * np.array(step1)
    A2 = np.array(pl.a2, dtype=np.float64) + k * np.array(step2)
    vec = A2 - A1
    d12 = np.linalg.norm(vec, axis=1)
    dp = np.divide(vec, d12[:, None], out=np.zeros_like(vec), where=d12[:, None] > 1e-12)
    n = np.floor(d12)                                   # last sample index of each row
    _check_width(float(n.max()))
    X1 = np.arange(int(n.max()) + 1, dtype=np.float64)[None, :]
    xcol = _round_np(dbc / 2.0 - d12[:, None] / 2.0 + X1)
    ok = (X1 <= n[:, None]) & (xcol >= 0) & (xcol < cols)
    lin = None                                          # flat voxel index, one contiguous (rows, K) array
    for axis, size in enumerate((sx, sy, sz)):
        i = _round_np(A1[:, axis, None] + X1 * dp[:, axis, None])
        ok &= (i >= 0) & (i < size)
        lin = i if lin is None else lin * size + i
    # M is C-contiguous [x,y,z] -> flat index (x*sy + y)*sz + z; invalid entries are masked below
    vals = M.reshape(-1).take(lin, mode="clip")
    dest = np.arange(rows, dtype=np.int64)[:, None] * cols + xcol
    dest[~ok] = rows * cols                             # trash slot for samples that are not written
    E = np.zeros(rows * cols + 1, dtype=M.dtype)
    E[dest] = vals
    return E[:rows * cols].reshape(rows, cols)


def project_py(vol, pl):
    """Pure-Python projection, same maths and rounding as project_np. Returns list of rows."""
    step1, step2, rows, cols, dbc = _geometry(pl)
    M, (sx, sy, sz) = vol.data, vol.shape
    sxy = sx * sy
    E = []
    for y in range(rows):
        k = y + 1.0
        a1 = [pl.a1[i] + k * step1[i] for i in range(3)]
        a2 = [pl.a2[i] + k * step2[i] for i in range(3)]
        vx, vy, vz = a2[0] - a1[0], a2[1] - a1[1], a2[2] - a1[2]
        d12 = math.sqrt(vx * vx + vy * vy + vz * vz)
        if d12 > 1e-12:
            dx, dy, dz = vx / d12, vy / d12, vz / d12
        else:
            dx = dy = dz = 0.0
        n = int(math.floor(d12))
        _check_width(n)
        row = [0] * cols
        for x1 in range(n + 1):
            x = round_nearest(dbc / 2.0 - d12 / 2.0 + x1)
            if not 0 <= x < cols:
                continue
            ix = round_nearest(a1[0] + x1 * dx)
            iy = round_nearest(a1[1] + x1 * dy)
            iz = round_nearest(a1[2] + x1 * dz)
            if 0 <= ix < sx and 0 <= iy < sy and 0 <= iz < sz:
                row[x] = M[ix + sx * iy + sxy * iz]
        E.append(row)
    return E