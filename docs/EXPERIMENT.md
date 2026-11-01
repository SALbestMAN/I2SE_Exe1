# Experiment Results

## Setup

- **Volume:** `data/MRHead_1.nrrd`, an MRI head scan, int16, 256×256×130 voxels.
- **Program:** Python 3 with NumPy, imageio, and ffmpeg.

## MRI demo

The program was run with `data/planes_demo.csv`. It created five video frames:

| Frame | Plane | Image size | Observation |
|---:|---|---:|---|
| 1 | Axial-aligned trapezoid | 255×255 | Shows the brain and surrounding anatomy |
| 2 | Axial-aligned trapezoid | 255×129 | Cut through the eyes and brain |
| 3 | Coronal-aligned trapezoid | 255×129 | Cut through the brain and neck |
| 4 | Oblique triangle | 180×187 | Triangle-shaped slice that widens across rows |
| 5 | Oblique trapezoid | 90×263 | Tilted slice through the head and face |

![MRI demo contact sheet](../results/contact_sheet.png)

The axis-aligned images match the corresponding volume slices. All frames use the same grayscale range and are centered on a black canvas.

## Invalid-plane demo

The program was run with `data/planes_invalid_demo.csv`. It created eight frames: three valid images and five marked error frames.

| Frame | Input | Result |
|---:|---|---|
| 1 | Valid trapezoid | Image |
| 2 | Triangle with unequal sides | Error frame |
| 3 | Valid trapezoid | Image |
| 4 | Trapezoid with an invalid base length | Error frame |
| 5 | Four points outside one plane | Error frame |
| 6 | Collinear triangle | Error frame |
| 7 | Malformed CSV row | Error frame |
| 8 | Valid triangle | Image |

![Invalid-plane contact sheet](../results/contact_sheet_errors.png)

Invalid rows produce marked frames without changing the order or results of valid rows.

## Class data results

Each available class volume was processed with its matching CSV file. The videos contain one frame per CSV row, and the planes produced non-empty images.

| Volume | Frames | Image size | Speed per plane (minimum / median / maximum FPS) |
|---|---:|---:|---:|
| Onion | 120 | 256×256 | 437 / 576 / 782 |
| Biscuit cake | 120 | 256×256 | 427 / 570 / 751 |
| Swiss roll | 120 | 256×256 | 341 / 468 / 600 |
| MRI head | 280 | 256×256 | 386 / 578 / 1301 |
| Croissant, 500×500×500 | 100 | About 500×560 | 55 / 82 / 102 |

The images show the expected layers and shapes. The 500×500×500 croissant volume met the minimum speed target of 30 FPS. Larger planes may run below the 100 FPS target.

## Performance

| Case | Measured speed |
|---|---:|
| MRI head planes | 260–1000 FPS |
| 500³ oblique plane, 721×300 | 74–124 FPS |
| 500³ full plane, 499×499 | 77–102 FPS |
| 500³ large plane, 706×706 | 35–46 FPS |

The measurements vary between runs because other processes may use the computer at the same time. All listed cases met the minimum 30 FPS target.

## Validation

- Projection results matched a simple reference implementation on random valid planes and supported data types.
- An independent nearest-neighbour check found no differing pixels across 25 sample planes.
- The output videos use H.264. Video compression causes small brightness differences from the original projected images.

## Summary and limits

The program creates projections for triangles and trapezoids, handles planes that extend outside the volume, and keeps one video frame for every CSV row. Invalid planes receive marked error frames.

Sampling uses the nearest voxel only. Coordinates are voxel indices; physical-space transforms from NRRD headers are not applied. Very large planes may be slower than 100 FPS, but the measured cases remained above 30 FPS.

