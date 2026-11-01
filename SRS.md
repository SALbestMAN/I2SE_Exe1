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

