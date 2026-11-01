# Data Set

## Volume files

| File | Size | What it contains |
|---|---:|---|
| `data/MRHead_1.nrrd` | 256×256×130 | MRI head scan used for the main example |
| `data/synthetic/index_u8_raw_15x16x1.nrrd` | 15×16×1 | Small 8-bit test volume with one layer |
| `data/synthetic/index_u16_gzip_40x30x20.nrrd` | 40×30×20 | Small 16-bit test volume |
| `data/synthetic/index_u32_gzip_be_50x60x70.nrrd` | 50×60×70 | 32-bit test volume using big-endian byte order |
| `data/synthetic/index_i16_raw_20x20x20.nrrd` | 20×20×20 | Signed 16-bit test volume |
| `data/synthetic/sphere_u8_gzip_64.nrrd` | 64×64×64 | Test volume containing nested spheres |
| `data/synthetic/tiny_u8_1x1x1.nrrd` | 1×1×1 | Smallest test volume: one voxel |
| `data/class_dataset/onion.nrrd` | 256×256×130 | Artificial onion with layers |
| `data/class_dataset/biscuit_cake.nrrd` | 256×256×130 | Artificial layered cake |
| `data/class_dataset/swiss_roll.nrrd` | 256×256×130 | Artificial spiral-shaped volume |
| `data/class_dataset/croissant.nrrd` | 500×500×500 | Croissant volume; the 63 MB file is not included |

The synthetic files are small test data included with the project. The `index` files have known voxel values, which makes it easier to check projection results. 
The performance test creates its large volume in memory; it does not need a saved 500×500×500 file.

## CSV files

- `data/planes_demo.csv` contains five valid planes for the MRI example.
- `data/planes_invalid_demo.csv` contains valid rows and examples of invalid or incomplete plane data.

## Class data

`data/class_dataset/` contains volumes, matching CSV files in `csv/`, and reference images in `images/`. The overview image is `images/overview.png`.

| CSV file | Volume | Number of planes |
|---|---|---:|
| `csv/onion.csv` | `onion.nrrd` | 120 |
| `csv/biscuit_cake.csv` | `biscuit_cake.nrrd` | 120 |
| `csv/swiss_roll.csv` | `swiss_roll.nrrd` | 120 |
| `csv/croissant.csv` | `croissant.nrrd` | 100 |
| `csv/head.csv` | `data/MRHead_1.nrrd` | 280 |

Some planes extend beyond their volume. The projection uses zero for points outside the volume.
