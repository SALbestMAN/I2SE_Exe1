# =============================================================================
# FILE OVERVIEW
# Defines the Volume object, which stores 3D voxel data and its dimensions and intensity range.
# =============================================================================


# =============================================================================
# EXPLANATION
# A container for a 3D NumPy data array, its shape, and the minimum and maximum voxel values.
# Code follows below.
# =============================================================================

class Volume:
    def __init__(self, data, shape):
        self.data, self.shape = data, shape
        self.vmin, self.vmax = float(data.min()), float(data.max())
