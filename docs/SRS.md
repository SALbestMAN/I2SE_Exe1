# Software Requirements Specification
## Ex1: 3D Volume Plane Projection

## 1. Introduction

### Purpose

This document states what the program must do. The program projects a 3D volume onto planes and saves the resulting images in a video.

### Readers

This document is for the course instructor, developers, and testers.

### Definitions

- **`volume`:** The 3D volume (class `Volume`). Its values are `volume.data[x][y][z]` and its dimensions are `volume.shape`.
- **Volume dimensions:** Each dimension is at least 1 and less than `2^10` (the assignment guarantees this; the program checks only that the volume is 3D with positive sizes).
- **Voxel coordinates:** Integer positions in the volume. The first voxel is `[0][0][0]`.
- **Plane:** Three points `(a,b,c)` for a triangle or four points `(a1,b,a2,c)` for a trapezoid.
- **Projection image:** The 2D image returned by `project(volume, plane)`.
- **`EPS`:** The geometry tolerance, set to `0.001` as specified in the instructor's Q&A.

## 2. Overall Description

### Product

The product is a command-line program:

```text
python Ex1.py file.nrrd file.csv file.mp4
```

The user may also set the optional `--fps` video playback rate.

### Environment

The program must work with Python 3.8 or later on any common operating system. It uses NumPy, pynrrd, imageio, imageio-ffmpeg, and Pillow. Install these libraries with:

```text
pip install -r requirements.txt
```

### Assumptions and Decisions

The assignment does not define every detail. The program uses these decisions:

- **A1. Coordinates:** Coordinates are voxel indices. They may be decimal values and may fall outside `volume`.
- **A2. Point order:** For four-point planes, the CSV order is `a1, b, a2, c`. The sides `a1 → b` and `a2 → c` are the two legs. For three-point planes, `a1 = a2 = a`.
- **A3. Sampling:** The program uses the nearest voxel. Exact half values, such as `x.5`, are rounded away from zero. A point outside `volume` has value 0.
- **A4. Image layout:** Each image row follows the movement from `a` toward `b`; row 0 is the first step. Columns follow `a1 → a2`. The image size is `row_count × column_count`, where `row_count = ceil(length_a1_to_b)` and `column_count = ceil(length_b_to_c)`; this matches the number of times the loop `y < length_a1_to_b` runs.

## 3. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | The program must start as `python Ex1.py <file.nrrd> <file.csv> <file.mp4>`. It may also accept `--fps`. |
| FR-2 | The program must read a 3D NRRD volume with supported 8-, 16-, or 32-bit unsigned values, as well as signed, 64-bit, and floating-point values. It must support raw and gzip encoding, little- and big-endian data, and LF or CRLF header lines. |
| FR-3 | The CSV must have a header row, then one plane per data row. A row starts with a point count of exactly 3 or 4 and has three finite coordinates per point. Missing coordinates, empty cells among required values, and extra non-empty values make the row invalid. Empty padding cells after the required values are allowed. |
| FR-4 | For each valid plane, the program must follow the assignment algorithm: move `a1` and `a2` one unit per row, sample integer steps `step_numbers = 0..floor(row_length)` from `a1` to `a2`, and calculate the destination column as `image_column = length_b_to_c/2 - row_length/2 + step_number`. Use the exact `length_b_to_c`, round the column to the nearest integer, and use zero for samples outside `volume`. |
| FR-5 | A sample outside the volume must have value 0. |
| FR-6 | The output video must contain exactly one frame per CSV data row, in the same order. |
| FR-7 | A valid 3-point plane must satisfy `abs(dist(a,b) - dist(a,c)) < EPS`. A valid 4-point plane must satisfy `abs(dist(a1,b) - dist(a2,c)) < EPS`, `dist(a1,a2) <= dist(b,c)`, and all four points must lie on one plane. For the last check, the fourth point must be within `EPS` of the plane made by the best group of three points. Coincident points and points all on one line are invalid. |
| FR-8 | Invalid plane geometry must raise `InvalidPlaneError`. The program must not silently correct the points or change the projection algorithm. |
| FR-9 | The demo program must catch invalid-plane errors and write an error frame for that row. The frame has a black background, a white cross, and the text `ERROR / PLANE #k`. Other valid planes must still produce their correct frames. Malformed CSV rows are handled in the same way. |
| FR-10 | All frames must have the same dimensions: the size of the largest valid plane, with a minimum of `160 × 100` when an error frame is present. Width and height must be even. All frames must use the same grayscale range based on the minimum and maximum values of `volume`. |
| FR-11 | Missing files, damaged or incomplete NRRD data, and unsupported formats must produce a clear `Error: ...` message and exit with status 1, without an unhandled traceback. |

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Performance:** For a `500³` volume, projection speed must be at least 30 fps. The expected target is at least 100 fps. This measures projection time only. |
| NFR-2 | **Robustness:** The program must not crash on planes partly or fully outside the volume, a `1 × 1 × 1` volume, or very large coordinates. A plane side longer than 4096 must be rejected before a huge image is allocated. |
| NFR-3 | **Portability:** Use Python and the four main libraries NumPy, pynrrd, imageio, and Pillow, with imageio-ffmpeg for video. Install them with one `pip install -r requirements.txt` command. The program must work on common operating systems. |
| NFR-4 | **Quality:** The code must be documented and unit-tested. The output must be deterministic for the same inputs. The code must be in a public repository with regular commits. |

## 5. Interfaces

- **NRRD input:** NRRD0004 header fields include `type`, `dimension=3`, `sizes`, `encoding`, and `endian`. The data is attached to the header.
- **CSV input:** The CSV layout is described in the README.
- **Video output:** The program writes a grayscale MP4 using H.264 and `yuv420p` through imageio and FFmpeg.

## 6. Acceptance

The tests in `docs/TESTING.md` must cover every functional and non-functional requirement.

The experiment in `docs/EXPERIMENT.md` demonstrates the command-line run, one frame per CSV row, and error frames for invalid planes.
