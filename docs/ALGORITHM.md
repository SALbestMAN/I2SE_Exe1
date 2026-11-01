# Algorithm Description
## 3D Volume Plane Projection

## 1. Overview

The program reads a 3D volume from an NRRD file and plane points from a CSV file.

For each plane, it samples values from the 3D volume and arranges them into a 2D grayscale image. It then combines the images into an MP4 video in the same order as the CSV rows.

## 2. Reading the Input Files

### 2.1 Reading the NRRD File

The program reads the NRRD file and stores its values in a NumPy array called `M`.

The array has three dimensions, with shape `(sx, sy, sz)`. Each value in `M` represents one voxel in the 3D volume.

The program checks that the data has exactly three dimensions and that each dimension has a size greater than zero.

### 2.2 Reading the CSV File

The first row of the CSV file is treated as a header. Each row after it describes one plane using either three or four 3D points.

- Three points describe a triangle.
- Four points describe a trapezoid.
- Each point has three coordinates: `x`, `y`, and `z`.

The program checks that each row contains the required number of coordinates and that the coordinates are valid finite numbers. An invalid row is kept in its position so the video frame order still matches the CSV row order.

## 3. Checking the Plane Points

Before projecting a plane, the program checks that its points follow the required geometry rules. The allowed tolerance is:

```text
EPS = 0.001
```

### 3.1 Plane with Three Points

For points `a`, `b`, and `c`, the two sides from `a` must have almost the same length:

```text
|dist(a, b) - dist(a, c)| < EPS
```

The points must not all lie on one straight line, because points on a line do not form a plane with area.

### 3.2 Plane with Four Points

For points `a1`, `b`, `a2`, and `c`, the program checks that:

1. The sides `a1 → b` and `a2 → c` have almost the same length:

   ```text
   |dist(a1, b) - dist(a2, c)| < EPS
   ```

2. The distance from `a1` to `a2` is not greater than the distance from `b` to `c`:

   ```text
   dist(a1, a2) <= dist(b, c)
   ```

3. All four points lie on the same plane within the tolerance `EPS`.

The program checks the last condition by choosing three points that form the largest triangle, using them to define a plane, and measuring the fourth point's distance from it.

The points must also form a real plane rather than collapsing into one line. If a geometry check fails, the plane is invalid.

## 4. Calculating the Image Dimensions and Directions

The program calculates the relevant side lengths:

```text
Dab = distance from a1 to b
Dac = distance from a2 to c
Dbc = distance from b to c
```

It uses these lengths to calculate the image size:

```text
rows = ceil(Dab)
columns = ceil(Dbc)
```

`ceil` rounds a value up to the next whole number. The code subtracts a very small number before rounding to prevent tiny computer precision errors from adding an extra row or column.

The program also calculates a unit direction for each side. A unit direction points along the side and has a length of 1. These directions let the program move one unit at a time when calculating the image rows.

## 5. Creating the 2D Projection

The projection function creates a 2D image with the calculated number of rows and columns. It starts with zero values, so any position that receives no sample remains black.

### 5.1 Finding Each Row

For each row, the program moves one unit along both sides of the plane:

```text
a1 for this row = a1 + (y + 1) × direction_a1_to_b
a2 for this row = a2 + (y + 1) × direction_a2_to_c
```

These two points mark the beginning and end of the row inside the 3D volume.

### 5.2 Sampling Along the Row

The program calculates the distance between the row's endpoints and the direction from the first endpoint to the second.

It then samples points along the row in steps of one unit. For each step, the 3D position is:

```text
position = row start + step number × row direction
```

The step number starts at zero and continues up to the whole-number part of the row length.

### 5.3 Reading a Voxel

A calculated position may have decimal coordinates. The program rounds each coordinate to the nearest integer to find the voxel to read from `M`.

Exact half values are rounded away from zero. For example:

```text
 2.5 becomes  3
-2.5 becomes -3
```

If the voxel is inside the volume, the program reads its value. If it is outside the volume, its value is treated as zero.

### 5.4 Placing the Sample in the Image

The program centers each row within the image by calculating its destination column:

```text
column = round(Dbc / 2 - row_length / 2 + step number)
```

It uses the exact value of `Dbc` in this calculation. If the resulting column is outside the image, that sample is skipped.

### 5.5 Using NumPy

The program uses NumPy to calculate many row and sample positions together. This avoids doing every pixel calculation in a separate Python loop and makes the projection faster.

The NumPy version follows the same steps as the row-by-row description above. The test suite compares its results with a direct version of those steps.

## 6. Converting the Projection to Grayscale

The projected image contains values from the volume. The program converts them to grayscale values from 0 to 255 using the smallest and largest values in the full volume:

```text
smallest volume value → 0   (black)
largest volume value  → 255 (white)
```

It uses the same value range for every frame so that brightness is consistent throughout the video.

## 7. Preparing and Writing the Video

All video frames must have the same dimensions. The program finds the largest valid projection size and centers each image on a black background of that size.

If a plane is invalid or cannot be projected, the program creates an error frame showing `ERROR` and the plane's number in the CSV. It then continues with the remaining planes.

Finally, the program writes the frames to an MP4 video in CSV order.

## 8. Errors and Boundary Cases

- Invalid plane points cause that plane to be rejected and represented by an error frame.
- A CSV row with missing, extra, or invalid values is marked invalid and keeps its place in the video.
- Samples outside the 3D volume become black pixels.
- A plane or row that exceeds the allowed size is rejected to prevent an excessively large image.
- An unreadable or damaged NRRD file produces a clear error message.

## 9. Processing Speed

The program prints the time and processing speed for each plane. This speed measures how quickly the program calculates projections. The `--fps` option controls how quickly frames play in the output video; it does not make the projection calculation faster.

## 10. Final Result

The output is an MP4 video with one frame for each CSV data row. Valid planes produce grayscale projection images. Invalid planes produce error frames. The frame order matches the CSV row order.
