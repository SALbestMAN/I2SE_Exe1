# Software Requirements Specification (SRS)
## 3D Volume Plane Projection

## 1. Introduction

### 1.1 Purpose

The purpose of this document is to describe the requirements of the 3D Volume Plane Projection project.

It explains what the system should do, how users interact with it, and the requirements that the implementation must meet.

### 1.2 Scope

The system reads a 3D volume from an NRRD file and plane coordinates from a CSV file.

It uses the given points to define planes, generates a 2D image for each plane, and combines the images into an MP4 video.

The system is designed to process multiple planes in the order they appear in the CSV file.

### 1.3 Definitions

| Term | Description |
|---|---|
| 3D Volume | A dataset containing values in three dimensions. |
| NRRD | A file format used to store volume data. |
| Plane | A flat surface defined by a set of points. |
| CSV | A file containing point coordinates. |
| Projection | The process of sampling the 3D volume to create a 2D image. |
| Frame | One 2D image in the output video. |
| EPS | A small tolerance value used when checking distances. |

### 1.4 References

- Project assignment: Ex1 – Algorithm: Implementing a Plane Projection of 3D Volume.
- Course documentation guidelines.

---

## 2. Overall Description

### 2.1 Product Perspective

The system is a command-line application written in Python.

It receives a 3D volume file and a CSV file containing plane coordinates. It processes the planes and creates an MP4 video as output.

### 2.2 User Classes

The system is intended for:

- Students who want to process 3D volume data.
- Users who want to generate 2D plane images from a 3D volume.

### 2.3 Operating Environment

The system runs on a computer with:

- Python installed.
- The required Python libraries.
- Access to the input NRRD and CSV files.

### 2.4 Design and Implementation Constraints

- The system shall be implemented in Python.
- The input volume shall be provided in NRRD format.
- The plane coordinates shall be provided in CSV format.
- The output shall be an MP4 video.
- The system shall support volume dimensions where each dimension is at least 1 and smaller than 1024.
- The volume values shall use unsigned 8-bit, 16-bit, or 32-bit data types.

### 2.5 Assumptions and Dependencies

- The user provides the input files.
- The CSV file contains the coordinates required to define the planes.
- The required Python libraries are installed before running the program.
- The plane coordinates are interpreted according to the format defined in the assignment.

---

