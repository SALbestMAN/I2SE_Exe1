# Testing Strategy

## 1. Goals

The tests check every requirement in `docs/SRS.md`. They use exact expected results wherever possible, not only visual inspection.

The tests also run the command-line demo from input files through video creation.

## 2. Test Types

| Test area | What is checked | How the result is checked | Requirements |
|---|---|---|---|
| NRRD reader | Each data type, encoding, and byte order in the data set, plus a separate `.nhdr` header with a raw data file. | The loaded data must match `x + sx*y + sx*sy*z`, and its shape must be `(sx, sy, sz)`. | FR-2 |
| CSV reader | Three- and four-point rows, empty cells at the end, BOM/CRLF files, and invalid rows. | Valid points must match the expected coordinates. An invalid row must become a `None` placeholder for its error frame. | FR-3, FR-9 |
| Exact projection | Axis-aligned planes through an index-coded volume. | Each output pixel must equal the value of the voxel it came from. This detects swapped axes, off-by-one positions, and transposed images. | FR-4 |
| Points outside the volume | Planes partly or fully outside `M`. | Outside pixels must be zero; inside pixels must have exact expected values. | FR-5, NFR-2 |
| Geometry | A triangle compared with the same shape written as a trapezoid; image dimensions. | Compare the images and check that the size is `ceil(Dab) × ceil(Dbc)`. | FR-4 |
| Random-plane property | Random isosceles planes inside the volume. | Every nonzero pixel must come from a voxel within half a voxel diagonal of the plane. The index-coded volume identifies the source voxel. | FR-4 |
| Assignment algorithm comparison | A direct Python copy of the instructor's steps (`reference_projection`) compared with the implementation. It covers 30 random triangle and trapezoid planes on MRHead, valid instructor rows 1, 2, and 4, and all four data types. | The images must have exactly identical pixel values. | FR-4 |
| Independent SciPy check | SciPy `map_coordinates(order=0)` samples the same coordinates using nearest-neighbor sampling. This was run manually once. | No pixel differences on 25 random MRHead planes, covering 154,985 pixels. | FR-4 |
| Plane validity rules | Equal-side tolerance, `dist(a1,a2) <= dist(b,c)`, coplanarity tolerance, and collinear points. | `InvalidPlaneError` must occur exactly when a rule is broken. Examples include 0.0005 allowed vs. 0.002 rejected and 0.0004 allowed vs. 0.01 rejected. | FR-7, FR-8 |
| Hand-calculated projection | Plane `a1=(0,0,0)`, `b=(2,0,0)`, `a2=(1,0,0)`, `c=(1,2,0)` on a `3 × 3 × 1` index volume. | The expected image is `[[0,1,4],[2,5,7]]`, calculated by hand. The implementation must match it. | FR-4, FR-7 |
| NumPy write consistency | 300 planes with many half-integer offsets and negative coordinates. | No two samples in one row may target the same image column. The result must match the direct reference algorithm. | NFR-3 |
| Class data set | All five CSV files in `data/class_dataset/` with their matching volumes. | Every plane must be valid, each image must be nonempty, and each video must have one frame per CSV row. | FR-4, FR-7 |
| Floating-point rounding | A distance of `7.000000000000001`. | It must still produce 7 rows, not 8. | FR-4 |
| Error frames | `make_error_frame()` and a command-line run mixing valid, non-isosceles, malformed, and too-wide rows. | The error mark must be visible, the frame mostly black, and the video frame count must match the CSV rows. Neighboring valid frames must remain valid, and error labels must differ. | FR-6, FR-9 |
| Edge cases | `1 × 1 × 1` volume and oversized coordinates such as `1e7`. | The tiny volume must not crash. The oversized plane must raise `ValueError` before a huge allocation and become an error frame in the demo. | NFR-2 |
| Rounding | Exact half values, scalar vs. vectorized rounding, and non-integer `Dab`. | Values must match the expected rounding; rows must advance by unit steps and use `ceil(Dab)` rows. | FR-4 |
| Exact CSV point count | Three points with a fourth or fifth extra point, four points with a fifth point, empty padding, and missing trailing cells. | Extra points are rejected; permitted empty padding is accepted; the command-line program creates error frames for invalid rows. | FR-3, FR-9 |
| Input handling | CRLF NRRD header and CSV values such as `NaN`, `inf`, `3.5`, or missing coordinates. | Files and rows must be read or rejected according to the requirements. | FR-2, FR-3 |
| Command-line integration | Run the program with MRHead and CSV files. | Exit code must be 0, an MP4 must exist, frame count must equal CSV data row count even with invalid rows, and frame dimensions must be even. | FR-1, FR-6, FR-9 |
| Error messages | Missing files and damaged or incomplete NRRD files. | The process must exit with a nonzero status and print `Error: ...` without a traceback. | FR-11 |
| Performance | `500³` volumes with `uint8`, `uint16`, and `uint32` values and a large oblique plane. | At least 30 fps is a required pass condition. The 100 fps target is reported. Only projection time is measured. The test is skipped when NumPy is unavailable. | NFR-1 |
| Visual review | `results/contact_sheet.png` for MRHead. | The images should look like slices through a head. Results are documented in `EXPERIMENT.md`. | Acceptance |

## 3. Running the Tests

Run the full test suite:

```text
python -m unittest discover -s tests -v
```

The complete suite has 48 tests and takes about 7 seconds, including the `500³` performance test.


## 4. Entry and Exit Criteria

Every commit that changes `Ex1.py` must keep the test suite passing. Before a release or submission, all tests must pass and the experiment must be run again to regenerate `results/demo.mp4`.
