# Ex1-Algorithm-Implementing-a-plane-projection-of-3D-volume
# 3D Volume Plane Projection

## 1. Project Overview

This project implements an algorithm that takes a 3D medical volume and generates 2D images from planes defined by points inside the volume. The generated images are combined into an MP4 video.

## 2. Problem Statement

A 3D volume contains data in three dimensions. It is not always easy to examine specific planes inside this volume directly.

The goal of this project is to develop an algorithm that can read a 3D volume, calculate planes based on given points, and generate 2D images representing these planes.

## 3. Project Scope

The project focuses on implementing a plane projection algorithm for 3D volume data.

The system will:

- Read a 3D volume from an NRRD file.
- Read plane coordinates from a CSV file.
- Support planes defined by either 3 or 4 points.
- Calculate the required plane for each set of points.
- Sample the 3D volume to generate a 2D image for each plane.
- Handle points or samples that are outside the volume.
- Combine the generated images into an MP4 video.

## 4. Input and Output

### Input

The program receives three files:

- **NRRD file:** Contains the 3D volume data.
- **CSV file:** Contains the coordinates of the points used to define the planes.
- **MP4 file:** The output video filename.

### Output

The program generates an MP4 video containing one frame for each plane defined in the CSV file. The frames follow the same order as the planes in the CSV file.



## 5. Requirements

### Functional Requirements

- The system shall read 3D volume data from an NRRD file.
- The system shall read plane coordinates from a CSV file.
- The system shall support planes defined by 3 or 4 points.
- The system shall generate a 2D image for each valid plane.
- The system shall set samples outside the volume to zero.
- The system shall create an MP4 video from the generated images.

### Non-Functional Requirements

- The algorithm should be efficient.
- The system should handle different volume dimensions.
- The code should be clear and organized.
- The system should handle invalid inputs properly.

## 6. How to Run

Run the program using the following command:

```bash
python Ex0.py file.nrrd file.csv file.mp4
```

Replace the filenames with the paths to your input and output files.

## 7. Running Tests

Tests are used to check the correctness of the algorithm and verify that the system handles different inputs and situations.

Run the tests using:

```bash
python -m unittest discover -s tests -v
```


Changes should be tested before they are committed to the repository.
