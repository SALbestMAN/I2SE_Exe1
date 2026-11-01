<p align="right">
  <img src="https://github.com/user-attachments/assets/ddbb6961-2f80-4a1b-a36d-208701f05dec" width="170"/>
</p>

# Ex1: Algorithm: Implementing a plane projection of 3D volume

## 1. Project Overview

This project reads a 3D medical volume, creates 2D images from planes described by points, and combines the images into an MP4 video.

The program processes the planes in the same order as the data rows in the CSV file. A valid plane produces a grayscale image. An invalid plane or CSV row produces an error frame, while the other rows continue to be processed.

## 2. Problem Statement

A 3D volume stores data in three dimensions. It can be difficult to inspect a chosen plane inside the volume directly.

The goal of this project is to read a 3D volume, use points from a CSV file to define planes, and create a 2D image from the volume at each plane. The resulting images are saved as a video.

## 3. Project Scope

The project includes:

- Reading a 3D volume from an NRRD file.
- Reading plane coordinates from a CSV file.
- Supporting planes defined by either 3 or 4 points.
- Checking whether the points satisfy the required plane rules.
- Sampling the 3D volume to create one 2D image for each valid plane.
- Setting samples outside the volume to zero, which appears black.
- Creating an error frame for an invalid plane or CSV row.
- Combining all frames into an MP4 video in CSV order.
- Providing tests, sample NRRD data, and documented experiments.

The project does not include an interactive viewer, a graphical interface, interpolation beyond nearest-voxel sampling, or conversion from physical coordinates in the NRRD header.

## 4. Input and Output

### Input

The program uses three paths:

- **NRRD file:** Contains the 3D volume data.
- **CSV file:** Contains the points that define the planes.
- **MP4 file:** The name and location for the output video.

The CSV begins with a header row. Each data row starts with the point count, followed by three coordinates `(x, y, z)` for each point. Coordinates are voxel indices and may be outside the volume.

Example:

```csv
Number of Points (3 or 4),x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4
3,200,200,0,0,200,400,400,200,400,,,
4,200,0,0,200,0,500,200,400,0,200,400,500
```

The first row describes a triangle with 3 points. The second describes a trapezoid with 4 points. Empty padding cells after the required coordinates are allowed. Missing coordinates, invalid numbers, a point count other than 3 or 4, or extra non-empty values make that CSV row invalid.

### Output

The program creates an MP4 video with one frame for each CSV data row. Frames appear in the same order as the rows. Valid planes produce grayscale projection images. Invalid planes produce marked error frames.

All frames have the same dimensions. Smaller images are centered on a black background. The grayscale range is based on the minimum and maximum values of the full volume and is shared by every frame.

## 5. Requirements

### Functional Requirements

- The system shall read 3D volume data from an NRRD file.
- The system shall read plane coordinates from a CSV file with a header row.
- The system shall support planes defined by 3 points (a triangle) or 4 points (a trapezoid).
- The system shall check that the points satisfy the plane rules described in section 9.
- The system shall generate a 2D image for each valid plane.
- The system shall use the nearest voxel when sampling the volume.
- The system shall set samples outside the volume to zero.
- The system shall keep one output frame for each CSV data row, including invalid rows.
- The system shall create an MP4 video from the generated frames.
- The system shall report input and format errors clearly.

### Non-Functional Requirements

- For a `500 × 500 × 500` volume, projection speed must be at least 30 planes per second. The expected target is at least 100 planes per second. This measures projection time, not video playback speed.
- The system should handle different volume dimensions, planes partly or fully outside the volume, and volumes as small as `1 × 1 × 1`.
- The system should reject excessively large planes before allocating a very large image.
- The code should be clear, organized, documented, and tested.
- The program should run on common operating systems using Python and the required libraries.

## 6. How to Run

Python 3.8 or later is required. From the project folder, install the required libraries once:

```bash
python3 -m pip install -r requirements.txt
```

Run the program with an NRRD file, a CSV file, and an output video path:

```bash
python3 Ex1.py file.nrrd file.csv file.mp4
```

Example using the included files:

```bash
python3 Ex1.py data/MRHead_1.nrrd data/planes_demo.csv results/demo.mp4
```

The optional `--fps` argument sets the video's playback speed:

```bash
python3 Ex1.py data/MRHead_1.nrrd data/planes_demo.csv results/demo.mp4 --fps 1
```

The `--fps` option does not change how fast the projection is calculated. If input paths are omitted, the program searches the project folder for the first NRRD and CSV files.

## 7. Running Tests

Tests check the reader, plane rules, projection results, edge cases, video creation, error handling, and performance.

Run all tests from the project folder:

```bash
python3 -m unittest discover -s tests -v
```

The full suite contains 48 tests and takes about 7 seconds, including the large-volume performance test. 

## 8. Project Structure

| Path | Contents |
|---|---|
| `Ex1.py` | The whole program in one file: NRRD and CSV reading, plane checks, projection, image processing, video writing, and the command-line demo. |
| `tests/` | Automated tests for the program. |
| `data/` | MRI volume, example CSV files, synthetic NRRD files, and the shared class data set. |
| `results/` | Generated videos, contact sheets, example frames, and run logs. |
| `docs/SRS.md` | Software requirements. |
| `docs/ALGORITHM.md` | Detailed description of the projection algorithm. |
| `docs/DATASET.md` | Description of the volume files and plane CSV files. |
| `docs/EXPERIMENT.md` | Experiment setup, results, and performance measurements. |
| `docs/TESTING.md` | Testing strategy and commands. |
| `requirements.txt` | Required Python libraries. |

## 9. Plane Rules and Sampling

The geometry tolerance is `EPS = 0.001`.

### Plane with 3 Points

For points `a`, `b`, and `c`, the distances from `a` to the other points must be almost equal:

```text
abs(dist(a, b) - dist(a, c)) < EPS
```

The three points must not all lie on one straight line.

### Plane with 4 Points

For points `a1`, `b`, `a2`, and `c`:

- `a1 → b` and `a2 → c` must have almost equal lengths:

  ```text
  abs(dist(a1, b) - dist(a2, c)) < EPS
  ```

- `dist(a1, a2)` must not be greater than `dist(b, c)`.
- All four points must lie on one plane within `EPS`.
- The points must not all lie on one line.

An invalid plane raises `InvalidPlaneError` in the projection code. When running the command-line program, that plane is shown as an error frame with a black background, a diagonal cross, a border, and the text `ERROR / PLANE #k`.

For sampling, the program rounds each 3D position to the nearest voxel. Exact half values are rounded away from zero: `2.5` becomes `3`, and `-2.5` becomes `-3`. If a position is outside the volume, its value is zero. The detailed steps and design decisions are in [`docs/ALGORITHM.md`](docs/ALGORITHM.md).

## 10. Example Results and Performance

- `data/planes_demo.csv` creates five valid projection frames.
- `data/planes_given.csv` creates four frames. Row 3 is invalid under the equal-side rule, so it becomes an error frame.
- `data/planes_invalid_demo.csv` demonstrates valid projections and error frames for invalid planes and CSV rows.

The videos, contact sheets, and run logs are in `results/`. The experiment report includes images and detailed results: [`docs/EXPERIMENT.md`](docs/EXPERIMENT.md).

In the documented `500³` measurements, typical planes ran at about 75–125 projections per second. A large `706 × 706` plane ran at about 35–46 projections per second. The required 30 fps was met in those measurements. See the experiment report for the test setup and full results.


## 11. Additional Material

| Material | Location |
|---|---|
| Demo, given csv, invalid-plane, and class videos | `results/` |
| Contact sheets and example frames | `results/contact_sheet*.png`, `results/demo_frame_*.png` |
| Run logs and benchmark details | `results/*_log.txt`, [`docs/EXPERIMENT.md`](docs/EXPERIMENT.md) |
| Requirements and algorithm | [`docs/SRS.md`](docs/SRS.md), [`docs/ALGORITHM.md`](docs/ALGORITHM.md) |
| Data set details | [`docs/DATASET.md`](docs/DATASET.md) |
| Test plan | [`docs/TESTING.md`](docs/TESTING.md) |
