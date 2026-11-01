# Algorithm Description
## 3D Volume Plane Projection

## 1. Overview

The algorithm takes a 3D volume from an NRRD file and a list of planes from a CSV file.

For each plane, it calculates a 2D image by taking samples from the 3D volume. After processing all planes, the images are combined into an MP4 video.

The algorithm follows the order of the planes in the CSV file.

