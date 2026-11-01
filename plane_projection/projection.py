# =============================================================================
# FILE OVERVIEW
# Samples voxel values along a plane and arranges them into a 2D grayscale image.
# =============================================================================

import math

import numpy as np

from plane_projection.geometry import MAX_SIDE, plane_geometry
from plane_projection.rounding import round_nearest


# =============================================================================
# EXPLANATION
# Projects the 3D volume onto the plane. It walks along each row of the plane, reads the volume value at each point, and stores that value in a 2D image.
# Code follows below.
# =============================================================================
def project(vol, pl):
    # Get the directions, image dimensions, and the distance between points b and c.
    direction_a1_to_b, direction_a2_to_c, rows, columns, distance_b_to_c = (
        plane_geometry(pl)
    )

    volume_data = vol.data
    volume_shape = vol.shape

    # Start with a black image. Each image position will hold one sampled volume value.
    image = np.zeros((rows, columns), dtype=volume_data.dtype)

    # Process one image row at a time.
    for row_index in range(rows):
        # The original algorithm starts the first row one step after a1 and a2.
        distance_along_side = row_index + 1

        # Find the left and right endpoints of this row in 3D space.
        left_point = [
            pl.a1[axis]
            + distance_along_side * direction_a1_to_b[axis]
            for axis in range(3)
        ]
        right_point = [
            pl.a2[axis]
            + distance_along_side * direction_a2_to_c[axis]
            for axis in range(3)
        ]

        # Find the direction and length from the left endpoint to the right endpoint.
        row_direction = [
            right_point[axis] - left_point[axis]
            for axis in range(3)
        ]
        row_length = math.sqrt(
            sum(component ** 2 for component in row_direction)
        )

        # Convert the row direction into a unit direction so each step is one unit long.
        if row_length > 1e-12:
            unit_direction = [
                component / row_length
                for component in row_direction
            ]
        else:
            # If the row has almost no length, do not move along it.
            unit_direction = [0.0, 0.0, 0.0]

        # The original algorithm samples whole-number steps up to the row length.
        last_step = math.floor(row_length)

        if last_step > 2 * MAX_SIDE:
            raise ValueError(
                "Plane too wide (row length %.0f)" % row_length
            )

        # Center this row's samples within the image columns.
        first_column_offset = (
            distance_b_to_c / 2.0 - row_length / 2.0
        )

        # Walk along the row, starting at step zero.
        for step_number in range(last_step + 1):
            column_index = round_nearest(
                first_column_offset + step_number
            )

            # Skip a sample if its image column is outside the image.
            if column_index < 0 or column_index >= columns:
                continue

            # Find this sample's 3D position.
            position = [
                left_point[axis]
                + step_number * unit_direction[axis]
                for axis in range(3)
            ]

            # Convert the 3D position to integer voxel coordinates.
            voxel = [
                round_nearest(position[axis])
                for axis in range(3)
            ]

            # Skip the sample if any coordinate is outside the volume.
            inside_volume = all(
                0 <= voxel[axis] < volume_shape[axis]
                for axis in range(3)
            )
            if not inside_volume:
                continue

            # Read the volume value and place it in the corresponding image pixel.
            image[row_index, column_index] = volume_data[
                voxel[0],
                voxel[1],
                voxel[2],
            ]

    return image