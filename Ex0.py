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

