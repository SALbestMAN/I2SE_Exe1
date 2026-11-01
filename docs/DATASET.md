# NRRD Data Set

## 1. Volume Files

| File | Data type | Encoding | Byte order | Dimensions | Purpose |
|---|---|---|---|---|---|
| `data/MRHead_1.nrrd` | `int16` | gzip | little-endian | `256 × 256 × 130` | Real MRI head scan from 3D Slicer; used in the main experiment. |
| `data/synthetic/index_u8_raw_15x16x1.nrrd` | `uint8` | raw | little-endian | `15 × 16 × 1` | Thin volume with depth 1; tests 8-bit data. |
| `data/synthetic/index_u16_gzip_40x30x20.nrrd` | `uint16` | gzip | little-endian | `40 × 30 × 20` | 16-bit volume with different axis sizes; helps detect x/y/z mix-ups. |
| `data/synthetic/index_u32_gzip_be_50x60x70.nrrd` | `uint32` | gzip | big-endian | `50 × 60 × 70` | Tests 32-bit values and big-endian byte order. |
| `data/synthetic/index_i16_raw_20x20x20.nrrd` | `int16` | raw | little-endian | `20 × 20 × 20` | Tests signed values and raw encoding. |
| `data/synthetic/sphere_u8_gzip_64.nrrd` | `uint8` | gzip | little-endian | `64 × 64 × 64` | Contains nested spheres for visual checks. |
| `data/synthetic/tiny_u8_1x1x1.nrrd` | `uint8` | raw | little-endian | `1 × 1 × 1` | Smallest allowed volume. |
| `data/class_dataset/onion.nrrd` | `uint8` | gzip | little-endian | `256 × 256 × 130` | Shared class data: onion with concentric layers. |
| `data/class_dataset/biscuit_cake.nrrd` | `uint16` | gzip | little-endian | `256 × 256 × 130` | Shared class data: layered biscuit cake. |
| `data/class_dataset/swiss_roll.nrrd` | `uint32` | gzip | little-endian | `256 × 256 × 130` | Shared class data: Swiss roll with a spiral shape. |
| `data/class_dataset/croissant.nrrd` | `uint8` | gzip | little-endian | `500 × 500 × 500` | Shared class data: croissant; the real 500³ test volume. It is not in the repository because it is 63 MB. Copy it from the class folder into `data/class_dataset/`. |
| Created by performance tests | `uint8`, `uint16`, or `uint32` | — | — | `500 × 500 × 500` | Made when needed for performance tests; not stored because each volume needs at least 125 MB. |

The synthetic files whose names start with `index_` store a unique value for each voxel:

```text
M[x, y, z] = x + sx × y + sx × sy × z
```

Because every voxel has a predictable value, tests can tell exactly which voxel supplied each pixel. Regenerate these files with:

```text
python tools/make_dataset.py
```

## 2. CSV Plane Lists

- `data/planes_given.csv` contains the instructor's example: two triangles and two trapezoids. Its coordinates go up to 500, so many parts of the planes fall outside the MRHead volume. Row 3, the second triangle, does not meet the equal-side rule: its side lengths are 497.4 and 476.9. It must produce an error frame.
- `data/planes_demo.csv` contains five valid planes inside MRHead: three axis-aligned planes (`z=65`, `y=128`, and `x=128`), one oblique triangle, and one oblique trapezoid.
- `data/planes_invalid_demo.csv` contains eight rows. It includes valid planes and examples of invalid input: a non-isosceles triangle, a trapezoid where `dist(a1,a2) > dist(b,c)`, four points that are not on one plane, a collinear triangle, and a malformed row that declares five points. A row with more coordinates than its declared point count also has an invalid format.

## 3. Shared Class Data Set

The class was asked to share one data set. A classmate provided it, and it is stored in `data/class_dataset/`. It includes volumes, one CSV per volume in `csv/`, and reference pictures in `images/`. The file `images/overview.png` shows the expected axial, coronal, sagittal, and oblique views for each volume.

The class folder's `MRHead_1.nrrd` and `lecturer_example.csv` are identical to `data/MRHead_1.nrrd` and `data/planes_given.csv`, so duplicate copies are not stored.

| CSV file | Matching volume | Rows and shape content |
|---|---|---|
| `csv/onion.csv`, `csv/biscuit_cake.csv`, `csv/swiss_roll.csv` | Volume with the same name | 120 rows each; all trapezoids. The planes tilt through the volume. Corners range from -47 to 302 in x/y and from -63 to 192 in z, so some points are outside the `256 × 256 × 130` volume. |
| `csv/croissant.csv` | `croissant.nrrd` | 100 rows; all triangles. Corners range from about -100 to 600, so many planes extend outside the `500³` volume. |
| `csv/head.csv` | `data/MRHead_1.nrrd` | 280 rows: 220 trapezoids and 60 triangles. It starts with consecutive axial slices (`z = 0, 1, 2, ...`), then includes tilted trapezoids and triangles. |

Every row in these CSV files is valid under the instructor's rules. The `TestClassDataset` tests check this.

