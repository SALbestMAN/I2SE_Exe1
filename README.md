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
