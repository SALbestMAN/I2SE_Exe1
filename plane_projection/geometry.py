# =============================================================================
# FILE OVERVIEW
# Contains geometry constants and helper functions for validating the input points and calculating projection dimensions and directions.
# =============================================================================

import math

from plane_projection.errors import InvalidPlaneError


MAX_SIDE = 4096
EPS = 0.001



# =============================================================================
# EXPLANATION
# Returns the 3D vector pointing from point p to point q by subtracting p coordinates from q coordinates.
# Code follows below.
# =============================================================================

def vector(p, q):
    return [q[i] - p[i] for i in range(3)]



# =============================================================================
# EXPLANATION
# Returns the Euclidean length of vector v: the square root of the sum of its components squared.
# Code follows below.
# =============================================================================

def length(v):
    return math.sqrt(sum(t * t for t in v))



# =============================================================================
# EXPLANATION
# Returns the cross product of u and v, a vector perpendicular to both. Its length helps measure triangle area and test whether points are collinear.
# Code follows below.
# =============================================================================

def cross(u, v):
    return (u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])



# =============================================================================
# EXPLANATION
# Validates the triangle or trapezoid geometry, checks side-length and coplanarity rules, and calculates unit step directions plus the output image dimensions.
# Code follows below.
# =============================================================================

def plane_geometry(pl):
    side1 = vector(pl.a1, pl.b)
    side2 = vector(pl.a2, pl.c)
    dab, dac, dbc = math.dist(pl.a1, pl.b), math.dist(pl.a2, pl.c), math.dist(pl.b, pl.c)
    d12 = length(vector(pl.a1, pl.a2))

    if min(dab, dac, dbc) <= 1e-12:
        raise InvalidPlaneError("degenerate plane (coincident points)")
    if abs(dab - dac) >= EPS:
        raise InvalidPlaneError("|dist(a1,b) - dist(a2,c)| = %.4f is not < EPS (%g): not isosceles"
                                % (abs(dab - dac), EPS))

    if d12 > 1e-12:
        if d12 > dbc + 1e-9:
            raise InvalidPlaneError("dist(a1,a2) = %.4f exceeds dist(b,c) = %.4f" % (d12, dbc))
        check_four_points_coplanar(pl, longest_side=max(dab, dbc, d12))
    else:
        normal = cross(side1, side2)
        if length(normal) <= 1e-9 * dab * dac:
            raise InvalidPlaneError("degenerate plane (a, b, c are collinear)")

    rows, cols = math.ceil(dab - 1e-9), math.ceil(dbc - 1e-9)
    if rows > MAX_SIDE or cols > MAX_SIDE:
        raise ValueError("Plane too large (%dx%d, limit %d)" % (rows, cols, MAX_SIDE))
    step1 = [t / dab for t in side1]
    step2 = [t / dac for t in side2]
    return step1, step2, rows, cols, dbc



# =============================================================================
# EXPLANATION
# Checks whether the four trapezoid points lie in one plane within the EPS tolerance. It chooses the three points that define the largest triangle, then measures the remaining point’s distance from that plane.
# Code follows below.
# =============================================================================

def check_four_points_coplanar(pl, longest_side):
    points = (pl.a1, pl.b, pl.a2, pl.c)
    options = ((0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 3, 1), (1, 2, 3, 0))

    best_normal_length, best_normal, best_origin, best_left_over = None, None, None, None
    for p, q, r, left_over in options:
        normal = cross(vector(points[p], points[q]), vector(points[p], points[r]))
        normal_length = length(normal)
        if best_normal_length is None or normal_length > best_normal_length:
            best_normal_length, best_normal, best_origin, best_left_over = normal_length, normal, p, left_over

    if best_normal_length <= 1e-9 * longest_side ** 2:
        raise InvalidPlaneError("degenerate plane (all 4 points are collinear)")

    to_point = vector(points[best_origin], points[best_left_over])
    distance = abs(sum(best_normal[t] * to_point[t] for t in range(3))) / best_normal_length
    if distance >= EPS:
        raise InvalidPlaneError("the 4 points are not on one plane "
                                "(one point is %.4f off the plane of the other three)" % distance)
