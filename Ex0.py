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