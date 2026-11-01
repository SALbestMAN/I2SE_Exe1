# =============================================================================
# FILE OVERVIEW
# Package entry point: imports the main public classes, functions, and constants from the package modules. __all__ lists the names available when a caller imports everything from plane_projection.
# =============================================================================

from plane_projection.cli import main
from plane_projection.csv_reader import load_planes
from plane_projection.errors import InvalidPlaneError
from plane_projection.geometry import EPS, MAX_SIDE, plane_geometry
from plane_projection.imaging import make_error_frame, pad_gray, to_gray
from plane_projection.nrrd_reader import load_nrrd
from plane_projection.plane import Plane
from plane_projection.projection import project
from plane_projection.rounding import round_nearest, round_nearest_array
from plane_projection.video import write_video
from plane_projection.volume import Volume

__all__ = [
    "EPS",
    "InvalidPlaneError",
    "MAX_SIDE",
    "Plane",
    "Volume",
    "load_nrrd",
    "load_planes",
    "main",
    "make_error_frame",
    "pad_gray",
    "plane_geometry",
    "project",
    "round_nearest",
    "round_nearest_array",
    "to_gray",
    "write_video",
]
