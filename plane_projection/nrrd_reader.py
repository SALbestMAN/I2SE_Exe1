# =============================================================================
# FILE OVERVIEW
# Reads NRRD files and wraps their validated 3D data in a Volume object.
# =============================================================================

import nrrd
import numpy as np

from plane_projection.volume import Volume



# =============================================================================
# EXPLANATION
# Reads the NRRD file, converts NRRD parsing errors into a clear ValueError, verifies that the data has three nonempty dimensions, and returns a Volume with contiguous data.
# Code follows below.
# =============================================================================

def load_nrrd(path):
    try:
        data, _header = nrrd.read(path)
    except nrrd.NRRDError as exc:
        raise ValueError("Invalid NRRD file: %s" % exc) from exc
    if data.ndim != 3 or min(data.shape) <= 0:
        raise ValueError("NRRD volume must be 3D with positive sizes (got shape %s)" % (data.shape,))
    return Volume(np.ascontiguousarray(data), data.shape)
