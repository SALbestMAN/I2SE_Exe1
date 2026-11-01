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

