# Algorithm Description
## 3D Volume Plane Projection

## 1. Overview

The algorithm takes a 3D volume from an NRRD file and a list of planes from a CSV file.

For each plane, it calculates a 2D image by taking samples from the 3D volume. After processing all planes, the images are combined into an MP4 video.

The algorithm follows the order of the planes in the CSV file.

## 2. Reading the Input Files

### 2.1 Reading the NRRD File

First, the program reads the NRRD file using the `pynrrd` library.

The file contains a 3D volume, which is stored as a NumPy array called `M`.

The volume has three dimensions:

- `sx`: Size along the X axis.
- `sy`: Size along the Y axis.
- `sz`: Size along the Z axis.

The program checks that the volume has exactly three dimensions and that all dimensions have positive sizes.

### 2.2 Reading the CSV File

Next, the program reads the CSV file.

Each data row contains either 3 or 4 points. Each point has three coordinates: X, Y, and Z.

- **3 points:** Define an isosceles triangle.
- **4 points:** Define an isosceles trapezoid.

The program skips the CSV header and reads the remaining rows.

It also checks that each row contains the correct number of values and that all coordinates are valid numbers.

If a row is invalid, the program marks it as invalid and continues reading the other rows.

## 3. Plane Validation

Before generating an image, the program checks whether the given points define a valid plane.

The tolerance value is:

`EPS = 0.001`

### 3.1 Plane Defined by 3 Points

The three points are:

- `a`
- `b`
- `c`

The program calculates the distances:

- `Dab`: Distance between a and b.
- `Dac`: Distance between a and c.

The plane is valid if:

`|Dab - Dac| < EPS`

The program also checks that the three points are not on the same straight line.

### 3.2 Plane Defined by 4 Points

The four points are:

- `a1`
- `b`
- `a2`
- `c`

The program checks the following conditions:

1. The distances from `a1` to `b` and from `a2` to `c` must be almost equal:

   `|dist(a1,b) - dist(a2,c)| < EPS`

2. The distance between `a1` and `a2` must not be greater than the distance between `b` and `c`:

   `dist(a1,a2) <= dist(b,c)`

3. All four points must lie on the same plane.

To check the third condition, the program finds the best combination of three points to define a plane. It then calculates the distance of the remaining point from that plane.

The distance must be smaller than `EPS`.

The program also checks that the points do not form a degenerate plane.

If any condition fails, the plane is considered invalid.

## 4. Calculating the Projection

After validating the plane, the program calculates the size of the output image and the direction of movement along the plane.

### 4.1 Calculating Distances

The program calculates:

- `Dab`: Distance from `a1` to `b`.
- `Dac`: Distance from `a2` to `c`.
- `Dbc`: Distance from `b` to `c`.

The number of rows is:

`rows = ceil(Dab)`

The number of columns is:

`cols = ceil(Dbc)`

The `ceil` function rounds the value up to the next integer.

### 4.2 Calculating Direction Vectors

The program calculates two direction vectors:

- From `a1` towards `b`.
- From `a2` towards `c`.

Each vector is divided by its length to create a unit vector.

A unit vector has a length of 1, so it moves exactly one unit at a time.

These vectors determine how the two sides of the plane move when generating each row of the image.

## 5. Generating the 2D Image

The main projection function is called `project()`.

It creates an empty 2D image called `E`, with the calculated number of rows and columns.

The image is initially filled with zeros.

### 5.1 Processing Each Row

For each row `y`, the program moves both starting points forward along their direction vectors.

The new points are calculated as follows:

`A1 = a1 + (y + 1) * step1`

`A2 = a2 + (y + 1) * step2`

These points define the beginning and end of the current row.

### 5.2 Sampling Between the Two Points

The program calculates the distance between `A1` and `A2`.

It then calculates a unit direction vector from `A1` to `A2`.

Starting from `A1`, the program samples points along this direction in steps of one unit.

The sample positions are:

`P = A1 + x1 * dp`

where `x1` starts at zero and increases by one until it reaches the last allowed sample.

### 5.3 Placing Samples in the Output Image

Each sampled point is converted into a column position in the output image.

The column is calculated using:

`xcol = round(Dbc / 2 - d12 / 2 + x1)`

This calculation centers the samples within the row.

The program uses the nearest integer when converting coordinates to voxel indices.

### 5.4 Checking Volume Boundaries

Before reading a value from the 3D volume, the program checks whether the sampled voxel is inside the volume boundaries.

If the sample is inside the volume, its value is copied into the corresponding position in the output image.

If the sample is outside the volume, its value remains zero.

This allows the algorithm to process planes that are partly or completely outside the volume.

### 5.5 Optimizing the Projection

The projection is implemented using NumPy vectorized operations.

Instead of using Python loops for every pixel, the program calculates many sample positions and their indices together.

This reduces the amount of Python-level work and improves processing speed.

After all samples are processed, the function returns the completed 2D image.

## 6. Converting the Image to Grayscale

After generating the projection, the program converts its values into grayscale values between 0 and 255.

It uses the minimum and maximum values of the original 3D volume.

Using the same range for all images helps keep the brightness consistent between video frames.

Values outside this range are clipped to the nearest limit.

## 7. Creating the Video

After processing all planes, the program prepares the images for the video.

All frames must have the same dimensions.

The program finds the largest valid image size and creates a black background with that size.

Each generated image is placed in the center of the background.

If a plane is invalid or its projection cannot be generated, the program creates an error frame instead. This frame contains the word `ERROR` and the plane number.

Finally, the program combines all frames into an MP4 video using the `imageio` library and the H.264 codec.

The video keeps the same order as the original CSV rows.

