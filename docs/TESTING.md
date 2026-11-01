# Testing

## Purpose

The tests check that the program reads its files, validates planes, creates correct projections, and writes videos as expected.

## What is checked

| Area | What the tests check |
|---|---|
| NRRD reading | Different data types, compression, byte order, file sizes, and damaged files |
| CSV reading | Triangles, trapezoids, blank cells, malformed rows, and extra values |
| Geometry | Valid and invalid planes, side lengths, coplanarity, and collinear points |
| Projection | Output size, correct voxel values, rounding, and points outside the volume |
| Video output | One frame per CSV row, including marked error frames for invalid rows |
| Input errors | Clear messages for missing or damaged files |
| Performance | Projection speed on large volumes |
| Class data | Plane lists produce valid, non-empty images |

The tests use the small files in `data/synthetic/`, the MRI file `data/MRHead_1.nrrd`, and files in `data/class_dataset/`. Some tests create temporary files or data in memory. The `croissant.nrrd` test is skipped if that file is not available.

## Run the tests

From the project folder, run:

```bash
python -m unittest discover -s tests -v
```

## Expected result

All available tests should pass. The speed test checks that projection reaches at least 30 frames per second on the tested large-volume cases.
