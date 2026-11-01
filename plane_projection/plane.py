# =============================================================================
# FILE OVERVIEW
# Defines the Plane data structure used to store the four points that describe a triangle or trapezoid.
# =============================================================================

from dataclasses import dataclass


@dataclass

# =============================================================================
# EXPLANATION
# A dataclass that stores four 3D points named a1, b, a2, and c. For a triangle, a1 and a2 refer to the same point; for a trapezoid they can differ.
# Code follows below.
# =============================================================================

class Plane:
    a1: tuple
    b: tuple
    a2: tuple
    c: tuple
