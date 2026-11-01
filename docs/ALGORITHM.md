# Main Algorithm
## Projecting a Plane from a 3D Volume

## 1. Checking Plane Points

The program checks the input points before it creates an image. The allowed distance tolerance is `EPS = 0.001`. If the points do not meet the rules, the program raises `InvalidPlaneError`. It does not change the points to make them valid.

### Plane with 3 Points

The points are `a`, `b`, and `c`. The distances from `a` to `b` and from `a` to `c` must be almost equal:

```text
abs(dist(a, b) - dist(a, c)) < EPS
```

The points must not all be on one straight line. Points on one line do not enclose a plane with area.

### Plane with 4 Points

The points are `a1`, `b`, `a2`, and `c`. The program checks that:

- The sides `a1 → b` and `a2 → c` have almost the same length:

  ```text
  abs(dist(a1, b) - dist(a2, c)) < EPS
  ```

- The distance from `a1` to `a2` is no greater than the distance from `b` to `c`:

  ```text
  dist(a1, a2) <= dist(b, c)
  ```

- All four points lie on one plane. The program chooses the three points that form the largest triangle, then checks that the remaining point is less than `EPS` away from their plane.
- The points do not all lie on one line.

The three points chosen to define the plane are not always `a1, b, a2`. For example, `a2` may lie on the line segment from `a1` to `b`, while the fourth point makes a valid plane:

```text
a1 = (0, 0, 0)
b  = (2, 0, 0)
a2 = (1, 0, 0)
c  = (1, 2, 0)
```

The video program catches an invalid-plane error and puts an error frame at that plane's position. The projection itself does not repair invalid points or change its unit-step rule.

## 2. Plane Measurements and Image Size

The input points are stored as `a1, b, a2, c`. For a triangle, `a1` and `a2` are the same point `a`.

```text
Dab = distance from a1 to b
Dac = distance from a2 to c
Dbc = distance from b to c
```

The two side directions are unit vectors:

```text
v(ab) = (b - a1) / Dab
v(ac) = (c - a2) / Dac
```

A unit vector points in the same direction as a side and has length 1. It lets the program move exactly one unit at a time.

The output image size is:

```text
rows = ceil(Dab)
columns = ceil(Dbc)
```

For row numbers `y = 0, 1, ..., rows - 1`, the row endpoints are:

```text
a1(y) = a1 + (y + 1) × v(ab)
a2(y) = a2 + (y + 1) × v(ac)
```

The `+1` means the first row is one unit step from the input points. The distance between the two endpoints is `d12`. The direction from the first endpoint to the second is:

```text
dp = (a2(y) - a1(y)) / d12
```

For a triangle, `d12` grows from almost zero at the tip to about `Dbc`. For a trapezoid, it starts at `dist(a1, a2)` and grows toward `Dbc`.

## 3. Projection Steps

The output image `E` starts with zeros. The program follows these steps for each row:

```text
E = zeros(rows, columns)

for each row y from 0 to rows - 1:
    calculate the row endpoints a1(y) and a2(y)
    calculate d12 and the direction dp

    for each integer step x1 from 0 through floor(d12):
        point = a1(y) + x1 × dp
        voxel_value = M[round(point)] if the voxel is inside M, otherwise 0
        column = round(Dbc / 2 - d12 / 2 + x1)

        if column is inside the image:
            E[y][column] = voxel_value

return E
```

The formula for `column` centers each row inside the full image width. It uses the exact `Dbc`, not the rounded column count.

## 4. Details the Assignment Does Not Specify

The program uses these rules to make the steps clear and consistent:

- **Voxel selection:** It uses the nearest voxel. Exact half values are rounded away from zero, so `2.5` becomes `3` and `-2.5` becomes `-3`. The scalar and NumPy array versions use the same rule, and tests compare them.
- **Column placement:** The calculated column is rounded to the nearest integer. Simply converting it to an integer could move a sample by as much as one pixel.
- **Samples beyond the image:** A sample whose column is outside `0` to `columns - 1` is skipped. This can happen for the final sample of a full-width row.
- **Small floating-point errors:** The code subtracts `1e-9` before applying `ceil` to a side length. For example, a true length of 7 may be returned as `7.000000000000001`. A direct `ceil` would incorrectly give 8 rows. A difference smaller than `1e-9` is treated as computer rounding noise; the geometry tolerance is much larger (`EPS = 0.001`).

## 5. NumPy Implementation

The simple steps above use a loop for every row and every sample. The implementation uses NumPy to calculate many rows and samples together, which reduces Python-level looping.

For a plane with `row_count` rows and up to `K` samples per row:

| Value | Meaning and shape |
|---|---|
| `left_endpoints`, `right_endpoints` | Start and end point for each row; shape `(row_count, 3)`. |
| `row_lengths` | The `d12` value for each row; shape `(row_count,)`. |
| `unit_directions` | The `dp` direction for each row; shape `(row_count, 3)`. |
| `step_numbers` | Sample numbers `0` through `K - 1`; shape `(1, K)`. |
| `image_columns` | Destination image column for each sample; shape `(row_count, K)`. |
| `voxel_indices` | Rounded voxel coordinate for one axis at a time; shape `(row_count, K)`. |
| `valid_samples` | Marks samples that are inside both the image and the volume. |

The implementation combines voxel coordinates into one position in a flattened array:

```text
flat position = (voxel_x × size_y + voxel_y) × size_z + voxel_z
(size_x, size_y, size_z are the three values of volume.shape)
```

Samples outside the volume receive a safe temporary read position and are then excluded by `valid_samples`; they are not written to the image.

The implementation writes invalid samples to one extra temporary image cell. That extra cell is removed before the final image is returned.

### Names Used in the Code

| Algorithm name | Name in `Ex1.py` |
|---|---|
| `M` | `volume.data` (`volume_data` inside `project`) |
| `E` | Returned image, reshaped to `row_count × column_count` |
| `Dab`, `Dbc` | `length_a1_to_b`, `length_b_to_c` (`distance_b_to_c` inside `project`) |
| `rows`, `columns` | `row_count`, `column_count` |
| `v(ab)`, `v(ac)` | `direction_a1_to_b`, `direction_a2_to_c` |
| `a1(y)`, `a2(y)` | `left_endpoints`, `right_endpoints` |
| `d12`, `dp` | `row_lengths`, `unit_directions` |
| `x1` | `step_numbers` |
| `x` | `image_columns` |
| Volume minimum and maximum | `volume.minimum_value`, `volume.maximum_value` |
| One CSV row | A `Plane` containing `a1`, `b`, `a2`, and `c` |

The tests include a direct Python version of the assignment steps called `reference_projection`. The optimized `project` function must produce exactly the same pixel values.

## 6. Processing Cost

For `rows` image rows and up to `K` samples per row:

- Projection time is about `O(rows × K)`, which is roughly `O(Dab × Dbc)`.
- Temporary memory is also about `O(rows × K)`, around 50 bytes per sample for the arrays used by the implementation.
- Loading the full volume takes time proportional to the number of voxels once per run.

Each plane side is limited to `MAX_SIDE = 4096`. A volume with dimensions `1023 × 1023 × 1023` has a diagonal of about 1772 voxels.

## 7. Edge Cases

| Case | Program behavior |
|---|---|
| Plane is partly or fully outside the volume | Samples outside the volume have value 0 and appear black. |
| The required side lengths are not almost equal | The plane is invalid and raises `InvalidPlaneError`. The video program writes an error frame. |
| Four-point plane has `dist(a1, a2) > dist(b, c)` | The plane is invalid. Equality is allowed. |
| Four points do not lie on one plane within `EPS` | The plane is invalid. |
| Required points coincide, or all points lie on one line | The plane is invalid. |
| `a1, b, a2` lie on a line, but all four points still define a plane | The plane may be valid; the program chooses the largest triangle to check coplanarity. |
| A plane side is longer than 4096, or a row is longer than 8192 | The plane is rejected before a very large image is created. |
| CSV row has a bad number, `NaN`, `inf`, wrong point count, missing coordinates, or extra non-empty values | The row is marked invalid and gets an error frame. Empty padding cells after the required coordinates are allowed. |
| NRRD axis order | The volume shape is `volume.shape` = `(size_x, size_y, size_z)` and the program accesses values as `volume.data[x][y][z]`. |
| NRRD header uses LF or CRLF line endings | Both are supported. Damaged or incomplete data gives a clear error. |

## 8. Grayscale Images and Error Frames

The program uses the full volume's minimum and maximum values to convert every projection to grayscale from 0 to 255. Using one range keeps brightness consistent between frames.

All frames are centered on a black canvas sized for the largest valid plane. If an error frame is needed, the canvas is at least 160 pixels wide and 100 pixels high. Its width and height are made even for the `yuv420p` video format.

An error frame has a black background, a white border, a diagonal cross, and the text `ERROR` and `PLANE #k`, where `k` is the plane's position in the CSV. The default video playback speed is 1 frame per second so each plane is visible.
