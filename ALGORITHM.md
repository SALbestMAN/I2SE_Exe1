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

