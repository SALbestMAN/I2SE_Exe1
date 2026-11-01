# =============================================================================
# FILE OVERVIEW
# Defines the rounding rule used for converting continuous coordinates to voxel and pixel indices.
# =============================================================================

import math

import numpy as np



# =============================================================================
# EXPLANATION
# Rounds one number to the nearest integer, sending exact halves away from zero (for example, 2.5 to 3 and -2.5 to -3).
# Code follows below.
# =============================================================================

def round_nearest(v):
    return int(math.floor(v + 0.5)) if v >= 0 else int(math.ceil(v - 0.5))



# =============================================================================
# EXPLANATION
# Applies the same nearest-integer rule to every value in a NumPy array and returns integer results.
# Code follows below.
# =============================================================================

def round_nearest_array(values):
    rounded = np.floor(values + 0.5)
    if values.min() < 0:
        rounded -= (values < 0) & (rounded == values + 0.5)
    return rounded.astype(np.int64)
