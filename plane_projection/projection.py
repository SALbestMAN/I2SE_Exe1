# =============================================================================
# FILE OVERVIEW
# Contains the main projection algorithm, which samples voxels along the rows of a plane and assembles them into a 2D image.
# =============================================================================

import numpy as np

from plane_projection.geometry import MAX_SIDE, plane_geometry
from plane_projection.rounding import round_nearest_array



# =============================================================================
# EXPLANATION
# Projects volume vol onto plane pl. It calculates row endpoints, samples each row in unit steps, rounds 3D positions to voxel coordinates, ignores positions outside the volume, and returns a 2D NumPy image.
# Code follows below.
# =============================================================================

def project(vol, pl):
    step1, step2, rows, cols, dbc = plane_geometry(pl)
    M = vol.data

    row_number = np.arange(1, rows + 1, dtype=np.float64)[:, np.newaxis]
    left_end = np.array(pl.a1, dtype=np.float64) + row_number * np.array(step1)
    right_end = np.array(pl.a2, dtype=np.float64) + row_number * np.array(step2)

    direction = right_end - left_end
    d12 = np.linalg.norm(direction, axis=1)
    unit = np.divide(direction, d12[:, np.newaxis], out=np.zeros_like(direction),
                     where=d12[:, np.newaxis] > 1e-12)
    last_step = np.floor(d12)
    if last_step.max() > 2 * MAX_SIDE:
        raise ValueError("Plane too wide (row length %.0f)" % last_step.max())
    x1 = np.arange(int(last_step.max()) + 1, dtype=np.float64)[np.newaxis, :]

    column = round_nearest_array(dbc / 2.0 - d12[:, np.newaxis] / 2.0 + x1)
    is_written = (x1 <= last_step[:, np.newaxis]) & (column >= 0) & (column < cols)

    flat_index = None
    for axis, size in enumerate(vol.shape):
        position = left_end[:, axis][:, np.newaxis] + x1 * unit[:, axis][:, np.newaxis]
        voxel = round_nearest_array(position)
        is_written &= (voxel >= 0) & (voxel < size)
        flat_index = voxel if flat_index is None else flat_index * size + voxel
    values = M.reshape(-1).take(flat_index, mode="clip")

    target = np.arange(rows, dtype=np.int64)[:, np.newaxis] * cols + column
    target[~is_written] = rows * cols
    image = np.zeros(rows * cols + 1, dtype=M.dtype)
    image[target] = values
    return image[:rows * cols].reshape(rows, cols)
