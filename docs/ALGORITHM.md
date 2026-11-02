# Main Algorithm
## Projecting a Plane from a 3D Volume


## 1. Checking Plane Points

The function `_plane_geometry` checks the input points before an image is created. The allowed distance tolerance is `EPS = 0.001`. If the points do not meet the rules, the program raises `InvalidPlaneError`. It does not change the points to make them valid.

A `Plane` has four points: `plane.a1`, `plane.b`, `plane.a2`, and `plane.c`. For a triangle, `a2` is the same point as `a1`.

The lengths used by the checks are:

```text
length_a1_to_b = distance from a1 to b
length_a2_to_c = distance from a2 to c
length_b_to_c  = distance from b to c
length_a1_to_a2 = distance from a1 to a2
```

### Plane with 3 Points (a2 = a1)

The distances from `a1` to `b` and from `a1` to `c` must be almost equal:

```text
abs(length_a1_to_b - length_a2_to_c) < EPS
```

The three points must not all be on one straight line. Points on one line do not enclose a plane with area.

### Plane with 4 Points

The program checks that:

- The sides `a1 → b` and `a2 → c` have almost the same length:

  ```text
  abs(length_a1_to_b - length_a2_to_c) < EPS
  ```

- The distance from `a1` to `a2` is no greater than the distance from `b` to `c`:

  ```text
  length_a1_to_a2 <= length_b_to_c
  ```

- All four points lie on one plane. The function `_check_four_points_on_one_plane` chooses the three points that form the largest triangle, then checks that the remaining point is less than `EPS` away from their plane (`distance_from_plane < EPS`).
- The points do not all lie on one line.

The three points chosen to define the plane are not always `a1, b, a2`. For example, `a2` may lie on the line segment from `a1` to `b`, while the fourth point makes a valid plane:

```text
a1 = (0, 0, 0)
b  = (2, 0, 0)
a2 = (1, 0, 0)
c  = (1, 2, 0)
```

The video program (`_run`) catches an invalid-plane error and puts an error frame at that plane's position. The projection itself does not repair invalid points or change its unit-step rule.

## 2. Plane Measurements and Image Size

`_plane_geometry` returns the values that `project` needs:

```text
direction_a1_to_b = (b - a1) / length_a1_to_b
direction_a2_to_c = (c - a2) / length_a2_to_c
row_count    = ceil(length_a1_to_b)
column_count = ceil(length_b_to_c)
```

`direction_a1_to_b` and `direction_a2_to_c` are unit vectors. A unit vector points in the same direction as a side and has length 1. It lets the program move exactly one unit at a time. The function returns `length_b_to_c`, which `project` receives under the name `distance_b_to_c`.

The output image has `row_count` rows and `column_count` columns.

For every row, `project` uses the row numbers `row_numbers = 1, 2, ..., row_count`. The row endpoints are:

```text
left_endpoints  = a1 + row_numbers × direction_a1_to_b
right_endpoints = a2 + row_numbers × direction_a2_to_c
```

The numbering starts at 1, so the first row is one unit step from the input points. The vector between the two endpoints of a row is `row_directions`:

```text
row_directions = right_endpoints - left_endpoints
row_lengths    = length of each row in row_directions
unit_directions = row_directions / row_lengths
```

For a triangle, `row_lengths` grows from almost zero at the tip to about `distance_b_to_c`. For a trapezoid, it starts at `length_a1_to_a2` and grows toward `distance_b_to_c`.

## 3. Projection Steps

The output image starts with zeros. The program follows these steps for each row:

```text
image = zeros(row_count, column_count)

for each row from 0 to row_count - 1:
    last_steps[row] = floor(row_lengths[row])

    for each value in step_numbers from 0 through last_steps[row]:
        position      = left_endpoints[row] + step_numbers × unit_directions[row]
        voxel_indices = round(position)
        sampled_value = volume_data[voxel_indices] if voxel_indices is inside the volume, otherwise 0
        image_columns = round(distance_b_to_c / 2 - row_lengths[row] / 2 + step_numbers)

        if image_columns is inside the image:
            image[row][image_columns] = sampled_value

return image
```

The formula for `image_columns` centers each row inside the full image width. It uses the exact `distance_b_to_c`, not the rounded `column_count`.

## 4. Details the Assignment Does Not Specify

The program uses these rules to make the steps clear and consistent:

- **Voxel selection:** It uses the nearest voxel. Exact half values are rounded away from zero, so `2.5` becomes `3` and `-2.5` becomes `-3`. The scalar function `round_nearest` and the NumPy array function `_round_array_nearest` use the same rule, and tests compare them.
- **Column placement:** `image_columns` is rounded to the nearest integer. Simply converting it to an integer could move a sample by as much as one pixel.
- **Samples beyond the image:** A sample whose `image_columns` value is outside `0` to `column_count - 1` is skipped (`valid_samples` is false). This can happen for the final sample of a full-width row.
- **Small floating-point errors:** The code subtracts `1e-9` before applying `ceil` to a side length. For example, a true length of 7 may be returned as `7.000000000000001`. A direct `ceil` would incorrectly give 8 rows. A difference smaller than `1e-9` is treated as computer rounding noise; the geometry tolerance is much larger (`EPS = 0.001`).

## 5. NumPy Implementation

The simple steps above use a loop for every row and every sample. The function `project` uses NumPy to calculate many rows and samples together, which reduces Python-level looping.

For a plane with `row_count` rows and up to `K` samples per row (`K = max(last_steps) + 1`):

| Value | Meaning and shape |
|---|---|
| `row_numbers` | Row numbers `1` through `row_count`; shape `(row_count, 1)`. |
| `left_endpoints`, `right_endpoints` | Start and end point for each row; shape `(row_count, 3)`. |
| `row_lengths` | The length of each row; shape `(row_count,)`. |
| `unit_directions` | The unit direction of each row; shape `(row_count, 3)`. |
| `last_steps` | `floor(row_lengths)`: the last sample number of each row; shape `(row_count,)`. |
| `step_numbers` | Sample numbers `0` through `K - 1`; shape `(1, K)`. |
| `image_columns` | Destination image column for each sample; shape `(row_count, K)`. |
| `voxel_indices` | Rounded voxel coordinate for one axis at a time; shape `(row_count, K)`. |
| `valid_samples` | Marks samples that are inside both the image and the volume; shape `(row_count, K)`. |

The function loops over the three axes of `volume.shape` (`axis`, `axis_size`) and combines the `voxel_indices` of each axis into one position in a flattened array:

```text
flat_voxel_indices = flat_voxel_indices × axis_size + voxel_indices
```

After the three axes (x, y, z) this equals `(x × volume.shape[1] + y) × volume.shape[2] + z`. The values are then read with:

```text
sampled_values = volume_data.reshape(-1).take(flat_voxel_indices, mode="clip")
```

The `clip` mode gives samples outside the volume a safe temporary read position. They are then excluded by `valid_samples`; they are not written to the image.

The result is written into `flat_image`, whose size is `row_count × column_count + 1`. The positions are `flat_image_positions`; samples that are not valid are written to the one extra cell at the end. That extra cell is removed before the final image is returned, reshaped to `row_count × column_count`.

The tests include a direct Python version of the assignment steps called `reference_projection`. The optimized `project` function must produce exactly the same pixel values.

## 6. Processing Cost

For `row_count` image rows and up to `K` samples per row:

- Projection time is about `O(row_count × K)`, which is roughly `O(length_a1_to_b × length_b_to_c)`.
- Temporary memory is also about `O(row_count × K)`, around 50 bytes per sample for the arrays used by the implementation.
- Loading the full volume takes time proportional to the number of voxels once per run.

Each plane side is limited to `MAX_SIDE = 4096`. A volume with dimensions `1023 × 1023 × 1023` has a diagonal of about 1772 voxels.

## 7. Edge Cases

| Case | Program behavior |
|---|---|
| Plane is partly or fully outside the volume | Samples outside the volume have value 0 and appear black. |
| The required side lengths are not almost equal | The plane is invalid and raises `InvalidPlaneError`. The video program writes an error frame. |
| Four-point plane has `length_a1_to_a2 > length_b_to_c` | The plane is invalid. Equality is allowed. |
| Four points do not lie on one plane within `EPS` | The plane is invalid. |
| Required points coincide, or all points lie on one line | The plane is invalid. |
| `a1, b, a2` lie on a line, but all four points still define a plane | The plane may be valid; the program chooses the largest triangle to check coplanarity. |
| `row_count` or `column_count` is larger than `MAX_SIDE` (4096), or a row is longer than `2 × MAX_SIDE` (8192) | The plane is rejected with `ValueError` before a very large image is created. |
| CSV row has a bad number, `NaN`, `inf`, wrong point count, missing coordinates, or extra non-empty values | The row is marked invalid (`None` in the list from `load_planes`) and gets an error frame. Empty padding cells after the required coordinates are allowed. |
| NRRD axis order | The shape is `volume.shape` and the program accesses values as `volume.data[x][y][z]`. |
| NRRD header uses LF or CRLF line endings | Both are supported. Damaged or incomplete data gives a clear error. |

## 8. Grayscale Images and Error Frames

`to_gray` uses the full volume's `volume.minimum_value` and `volume.maximum_value` to convert every projection to grayscale from 0 to 255. Using one range keeps brightness consistent between frames.

`pad_gray` centers every image on a black canvas sized for the largest valid plane (`frame_height`, `frame_width`). If an error frame is needed, the canvas is at least 160 pixels wide and 100 pixels high. Its width and height are made even for the `yuv420p` video format.

`make_error_frame` draws a black background, a white border, a diagonal cross, and the text `ERROR` and `PLANE #k`, where `k` is the plane's position in the CSV (`plane_number`). The default video playback speed is 1 frame per second so each plane is visible.
