# =============================================================================
# FILE OVERVIEW
# Reads NRRD files, checks that they contain valid 3D data, and stores the data in a Volume object.
# =============================================================================

import nrrd
import numpy as np

from plane_projection.volume import Volume


# =============================================================================
# EXPLANATION
# Reads the NRRD file at path. If reading fails, raises a clear error. Then checks that the data has three nonempty dimensions and returns it inside a Volume object.
# Code follows below.
# =============================================================================
def load_nrrd(path):
    try:
        # Read the image data and its header from the NRRD file.
        data, header = nrrd.read(path)

    except nrrd.NRRDError as error:
        # Replace the library's parsing error with a message that identifies the file problem.
        raise ValueError("Invalid NRRD file: %s" % error) from error

    # A 3D volume must have exactly three dimensions.
    if data.ndim != 3:
        raise ValueError(
            "NRRD volume must have 3 dimensions, but got %d"
            % data.ndim
        )

    # Each dimension must contain at least one item.
    if min(data.shape) <= 0:
        raise ValueError(
            "NRRD volume dimensions must be greater than zero; got shape %s"
            % (data.shape,)
        )

    # Store the data contiguously in memory, then wrap it in a Volume object.
    contiguous_data = np.ascontiguousarray(data)
    return Volume(contiguous_data, contiguous_data.shape)