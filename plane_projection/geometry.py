# =============================================================================
# FILE OVERVIEW
# Contains geometry constants and helper functions for validating plane points and calculating projection directions and image dimensions.
# =============================================================================

import math

from plane_projection.errors import InvalidPlaneError


MAX_SIDE = 4096
EPSILON = 0.001
TINY_NUMBER = 1e-9


# =============================================================================
# EXPLANATION
# Returns the 3D vector pointing from point_a to point_b by subtracting their x, y, and z coordinates.
# Code follows below.
# =============================================================================
def vector_between(point_a, point_b):
    return [
        point_b[axis] - point_a[axis]
        for axis in range(3)
    ]


# =============================================================================
# EXPLANATION
# Calculates the length of a vector using the square root of the sum of its components squared.
# Code follows below.
# =============================================================================
def vector_length(vector):
    return math.sqrt(sum(component ** 2 for component in vector))


# =============================================================================
# EXPLANATION
# Returns a vector perpendicular to both input vectors. Its length is useful for checking whether points form an area or lie on one line.
# Code follows below.
# =============================================================================
def cross_product(vector_a, vector_b):
    return (
        vector_a[1] * vector_b[2] - vector_a[2] * vector_b[1],
        vector_a[2] * vector_b[0] - vector_a[0] * vector_b[2],
        vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0],
    )


# =============================================================================
# EXPLANATION
# Validates the plane points, checks the required side lengths, and calculates unit directions and the output image dimensions. A unit direction points the same way as a side but has a length of 1.
# Code follows below.
# =============================================================================
def plane_geometry(plane):
    # Build direction vectors for the two sides used to move across the plane.
    side_a1_to_b = vector_between(plane.a1, plane.b)
    side_a2_to_c = vector_between(plane.a2, plane.c)

    # Calculate the lengths of the relevant sides and point-to-point distance.
    length_a1_to_b = math.dist(plane.a1, plane.b)
    length_a2_to_c = math.dist(plane.a2, plane.c)
    length_b_to_c = math.dist(plane.b, plane.c)
    length_a1_to_a2 = math.dist(plane.a1, plane.a2)

    # Reject a plane if any required side has zero or almost-zero length.
    if min(length_a1_to_b, length_a2_to_c, length_b_to_c) <= 1e-12:
        raise InvalidPlaneError("degenerate plane (coincident points)")

    # The two sides are expected to have nearly equal lengths.
    if abs(length_a1_to_b - length_a2_to_c) >= EPSILON:
        difference = abs(length_a1_to_b - length_a2_to_c)
        raise InvalidPlaneError(
            "|dist(a1,b) - dist(a2,c)| = %.4f is not < EPSILON (%g): not isosceles"
            % (difference, EPSILON)
        )

    # If a1 and a2 differ, this is a four-point plane, so check all four points.
    if length_a1_to_a2 > 1e-12:
        if length_a1_to_a2 > length_b_to_c + 1e-9:
            raise InvalidPlaneError(
                "dist(a1,a2) = %.4f exceeds dist(b,c) = %.4f"
                % (length_a1_to_a2, length_b_to_c)
            )

        check_four_points_coplanar(
            plane,
            longest_side=max(length_a1_to_b, length_b_to_c, length_a1_to_a2),
        )

    # If a1 and a2 are the same point, validate the three-point plane instead.
    else:
        normal = cross_product(side_a1_to_b, side_a2_to_c)
        area_measure = vector_length(normal)

        if area_measure <= 1e-9 * length_a1_to_b * length_a2_to_c:
            raise InvalidPlaneError("degenerate plane (a, b, c are collinear)")

    # Convert side lengths to whole-number image rows and columns.
    # TINY_NUMBER avoids rounding a value such as 5.0000000001 up to 6
    # when the intended length is effectively 5.
    rows = math.ceil(length_a1_to_b - TINY_NUMBER)
    columns = math.ceil(length_b_to_c - TINY_NUMBER)

    if rows > MAX_SIDE or columns > MAX_SIDE:
        raise ValueError(
            "Plane too large (%dx%d, limit %d)" % (rows, columns, MAX_SIDE)
        )

    # Divide each vector component by the side length to get a unit direction.
    direction_a1_to_b = [
        component / length_a1_to_b
        for component in side_a1_to_b
    ]
    direction_a2_to_c = [
        component / length_a2_to_c
        for component in side_a2_to_c
    ]

    return (
        direction_a1_to_b,
        direction_a2_to_c,
        rows,
        columns,
        length_b_to_c,
    )


# =============================================================================
# EXPLANATION
# Checks whether four points lie on the same plane within the EPSILON tolerance. It chooses the three points that form the largest triangle, then measures the fourth point's distance from their plane.
# Code follows below.
# =============================================================================
def check_four_points_coplanar(plane, longest_side):
    points = (plane.a1, plane.b, plane.a2, plane.c)

    # Each option selects three points for a plane and leaves one point to test.
    possible_groups = (
        (0, 1, 2, 3),
        (0, 1, 3, 2),
        (0, 2, 3, 1),
        (1, 2, 3, 0),
    )

    best_normal = None
    best_normal_length = 0
    best_origin_index = None
    point_to_check_index = None

    # Choose the triple with the largest triangle area for a more stable check.
    for first, second, third, leftover in possible_groups:
        vector_1 = vector_between(points[first], points[second])
        vector_2 = vector_between(points[first], points[third])
        normal = cross_product(vector_1, vector_2)
        normal_length = vector_length(normal)

        if normal_length > best_normal_length:
            best_normal = normal
            best_normal_length = normal_length
            best_origin_index = first
            point_to_check_index = leftover

    # If every possible triangle has almost no area, the points are collinear.
    if best_normal_length <= 1e-9 * longest_side ** 2:
        raise InvalidPlaneError("degenerate plane (all 4 points are collinear)")

    # Find a vector from the selected plane origin to the remaining point.
    vector_to_leftover = vector_between(
        points[best_origin_index],
        points[point_to_check_index],
    )

    # Calculate the perpendicular distance from the remaining point to the plane.
    distance_from_plane = abs(
        sum(
            best_normal[axis] * vector_to_leftover[axis]
            for axis in range(3)
        )
    ) / best_normal_length

    if distance_from_plane >= EPSILON:
        raise InvalidPlaneError(
            "the 4 points are not on one plane "
            "(one point is %.4f off the plane of the other three)"
            % distance_from_plane
        )
