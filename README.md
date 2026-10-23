# Ex1-Algorithm-Implementing-a-plane-projection-of-3D-volume

## Problem Statement

The goal of this project is to implement an algorithm that extracts a two-dimensional image representing a specified plane within a three-dimensional volumetric data matrix.

The program receives a 3D volume in NRRD format and plane coordinates from a CSV file. It computes an image for each specified plane and combines the resulting images into an MP4 video.


## Project Scope

The project aims to design and implement an algorithm that projects specified planes from a three-dimensional volumetric data matrix into two-dimensional images.

The program will:

* Input Handling: Read a 3D volumetric data file in NRRD format and a CSV file containing the coordinates of three or four points defining each plane.
* Plane Projection: Compute a 2D image representing each specified plane using the 3D volume data.
* Output Generation: Generate an MP4 video containing one frame for each plane, preserving the order of the planes in the CSV file.
* Correctness: Produce correct projection results according to the defined algorithm and design.
* Stability and Robustness: Handle input data and boundary cases reliably, including points that fall outside the volume, according to the defined design.
* Runtime Efficiency: Meet the assignment’s performance requirements for processing a 3D matrix of size (500^3). The expected runtime performance is at least 100 FPS, and an additional 30 FPS is mandatory.
* Code Quality: Prioritize a clear, maintainable, and well-structured implementation, with emphasis on software design and overall code quality.

The program will be executed from the command line using the following format: python Ex0.py file.nrrd file.csv file.mp4
