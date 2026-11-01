# =============================================================================
# FILE OVERVIEW
# Defines a dedicated exception type for invalid plane geometry.
# =============================================================================


# =============================================================================
# EXPLANATION
# A ValueError subclass used when a plane fails the geometry rules. The pass statement means this class adds a distinct name and type without extra behavior.
# Code follows below.
# =============================================================================

class InvalidPlaneError(ValueError):
    pass
