"""Automated tests for Ex1.py.   Run:  python -m unittest discover -s tests -v"""

import contextlib
import io
import math
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import plane_projection as pp  

import numpy as np  
SYN = os.path.join(ROOT, "data", "synthetic")
MRHEAD = os.path.join(ROOT, "data", "MRHead_1.nrrd")


def P(*pts):
    """Plane from 3 (a,b,c) or 4 (a',b,a'',c) points."""
    pts = [tuple(map(float, p)) for p in pts]
    return pp.Plane(pts[0], pts[1], pts[0], pts[2]) if len(pts) == 3 else pp.Plane(*pts)


def write_file(path, data, mode="w"):
    with open(path, mode) as f:
        f.write(data)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def quiet(fn, *a, **k):
    with contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def index_value(x, y, z, shape):
    return x + shape[0] * y + shape[0] * shape[1] * z


# ---------------------------------------------------------------- NRRD reader
class TestNrrdReader(unittest.TestCase):
    CASES = [("index_u8_raw_15x16x1.nrrd", (15, 16, 1), "uint8"),
             ("index_u16_gzip_40x30x20.nrrd", (40, 30, 20), "uint16"),
             ("index_u32_gzip_be_50x60x70.nrrd", (50, 60, 70), "uint32"),
             ("index_i16_raw_20x20x20.nrrd", (20, 20, 20), "int16")]

    # Checks supported numeric types, raw/gzip encoding, byte order, dimensions, and voxel values using synthetic NRRD files.
    def test_all_dtypes_encodings_endianness(self):
        for name, shape, dtype in self.CASES:
            with self.subTest(name):
                v = pp.load_nrrd(os.path.join(SYN, name))
                self.assertEqual(v.shape, shape)
                self.assertEqual(v.data.dtype.name, dtype)
                x, y, z = np.meshgrid(*(np.arange(s) for s in shape), indexing="ij")
                self.assertTrue(np.array_equal(v.data, x + shape[0] * y + shape[0] * shape[1] * z))

    # Checks that the real MRI NRRD loads with the expected dimensions and a nonzero value range.
    def test_real_mri(self):
        v = pp.load_nrrd(MRHEAD)
        self.assertEqual(v.shape, (256, 256, 130))
        self.assertGreater(v.vmax, v.vmin)

    # Checks that a one-voxel synthetic NRRD loads correctly.
    def test_tiny_volume(self):
        self.assertEqual(pp.load_nrrd(os.path.join(SYN, "tiny_u8_1x1x1.nrrd")).shape, (1, 1, 1))

    # Checks that an NRRD file missing its final data bytes is rejected.
    def test_truncated_file_raises(self):
        raw = read_bytes(os.path.join(SYN, "index_i16_raw_20x20x20.nrrd"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.nrrd")
            write_file(p, raw[:-100], "wb")
            with self.assertRaises(ValueError):
                pp.load_nrrd(p)

    # Checks that an NRRD header can read voxel data stored in a separate raw file.
    def test_detached_header_and_data_file(self):
        with tempfile.TemporaryDirectory() as d:
            vals = np.arange(4 * 3 * 2, dtype="<u2")
            write_file(os.path.join(d, "v.raw"), vals.tobytes(), "wb")
            write_file(os.path.join(d, "v.nhdr"), "NRRD0004\ntype: ushort\ndimension: 3\nsizes: 4 3 2\n"
                       "encoding: raw\nendian: little\ndata file: v.raw\n\n")
            v = pp.load_nrrd(os.path.join(d, "v.nhdr"))
            self.assertEqual(v.shape, (4, 3, 2))
            self.assertEqual(int(v.data[3, 2, 1]), 3 + 4 * 2 + 12 * 1)

    # Checks that a file without a valid NRRD signature is rejected.
    def test_bad_magic_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.nrrd")
            write_file(p, b"HELLO\n\n", "wb")
            with self.assertRaises(ValueError):
                pp.load_nrrd(p)


# ----------------------------------------------------------------- CSV reader
class TestCsv(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "p.csv")
            with open(p, "w", newline="", encoding="utf-8") as f:
                f.write(text)
            return quiet(pp.load_planes, p)

    HDR = "Number of Points (3 or 4),x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\r\n"

    # Checks that CSV rows for a triangle and trapezoid become Plane objects with the right coordinates.
    def test_triangle_and_trapezoid(self):
        pl = self._load(self.HDR + "3,1,2,3,4,5,6,7,8,9,,,\r\n4,0,0,0,0,0,5,0,4,0,0,4,5\r\n")
        self.assertEqual(len(pl), 2)
        self.assertEqual((pl[0].a1, pl[0].b, pl[0].a2, pl[0].c),
                         ((1, 2, 3), (4, 5, 6), (1, 2, 3), (7, 8, 9)))
        self.assertEqual((pl[1].a1, pl[1].b, pl[1].a2, pl[1].c),
                         ((0, 0, 0), (0, 0, 5), (0, 4, 0), (0, 4, 5)))

    # Checks CSV reading with a UTF-8 BOM and blank lines, and loads all rows from the instructor CSV.
    def test_bom_blank_lines_and_instructor_file(self):
        self.assertEqual(len(self._load("\ufeff" + self.HDR + "\r\n3,1,1,1,2,2,2,3,3,3,,,\r\n")), 1)
        pl = quiet(pp.load_planes, os.path.join(ROOT, "data", "planes_instructor.csv"))
        self.assertEqual([p is not None for p in pl], [True] * 4)

    # Checks that malformed CSV rows become None without shifting the remaining row positions.
    def test_bad_rows_keep_their_slot(self):
        pl = self._load(self.HDR + "3,1,2,3\r\nabc,1\r\n5,1,2,3\r\n3,1,1,1,2,2,2,3,3,3,,,\r\n")
        self.assertEqual(len(pl), 4)
        self.assertEqual([p is None for p in pl], [True, True, True, False])


# ----------------------------------------------------------------- projection
class TestProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        cls.M = cls.vol.data   # M[x,y,z] == index code

    # Checks exact voxel values and image dimensions for a plane aligned with the z axis.
    def test_axis_aligned_z_plane_exact(self):
        # rows follow y (a'->b), columns follow x : E[y][x] = M[x][y+1][z]
        E = pp.project(self.vol, P((0, 0, 7), (0, 29, 7), (39, 0, 7), (39, 29, 7)))
        self.assertEqual(E.shape, (29, 39))
        self.assertTrue(np.array_equal(E, self.M[:39, 1:30, 7].T))

    # Checks exact voxel values for planes aligned with the x and y axes.
    def test_axis_aligned_x_and_y_planes_exact(self):
        Ex = pp.project(self.vol, P((12, 0, 0), (12, 0, 19), (12, 29, 0), (12, 29, 19)))
        self.assertTrue(np.array_equal(Ex, self.M[12, :29, 1:20].T))   # rows follow z, cols follow y
        Ey = pp.project(self.vol, P((0, 5, 0), (0, 5, 19), (39, 5, 0), (39, 5, 19)))
        self.assertTrue(np.array_equal(Ey, self.M[:39, 5, 1:20].T))

    # Checks that a triangle and an equivalent trapezoid with the same starting point produce identical images.
    def test_triangle_equals_degenerate_trapezoid(self):
        a, b, c = (20, 0, 0), (5, 29, 19), (35, 29, 19)
        self.assertTrue(np.array_equal(pp.project(self.vol, P(a, b, c)),
                                       pp.project(self.vol, P(a, b, a, c))))

    # Checks that projected image dimensions match the required side lengths rounded up.
    def test_output_size_is_Dab_by_Dbc(self):
        a, b, c = (20, 0, 0), (5, 29, 19), (35, 29, 19)
        E = pp.project(self.vol, P(a, b, c))
        dab = sum((i - j) ** 2 for i, j in zip(a, b)) ** .5
        dbc = sum((i - j) ** 2 for i, j in zip(b, c)) ** .5
        self.assertEqual(E.shape, (math.ceil(dab - 1e-9), math.ceil(dbc - 1e-9)))

    # Checks that samples outside the volume become zero while in-volume samples stay correct.
    def test_outside_volume_is_zero(self):
        E = pp.project(self.vol, P((100, 100, 100), (100, 100, 150), (150, 100, 100), (150, 100, 150)))
        self.assertEqual(E.shape, (50, 50))
        self.assertFalse(E.any())
        # half inside / half outside: inside part exact, outside part zero
        E = pp.project(self.vol, P((0, 0, 7), (0, 29, 7), (79, 0, 7), (79, 29, 7)))
        self.assertEqual(E.shape, (29, 79))
        self.assertTrue(np.array_equal(E[:, :40], self.M[:40, 1:30, 7].T))   # inside part exact
        self.assertFalse(E[:, 40:].any())                                  # outside part black

    # Checks rejection of non-isosceles triangles and acceptance/rejection around the EPS tolerance.
    def test_non_isosceles_raises(self):
        """Q&A 1/3a: |dist(a,b) - dist(a,c)| must be < EPS = 0.001, otherwise an exception."""
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(self.vol, P((20, 0, 0), (5, 29, 19), (35, 20, 10)))
        # just inside / just outside the tolerance
        a, b = (0.0, 0.0, 7.0), (0.0, 10.0, 7.0)
        pp.project(self.vol, P(a, b, (10.0, 0.0005, 7.0)))            # |dab-dac| ~ 0.0005 -> valid
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(self.vol, P(a, b, (0.0, -10.002, 7.0)))        # |dab-dac| = 0.002 -> invalid

    # Checks that coincident points that cannot define a plane raise InvalidPlaneError.
    def test_degenerate_plane_raises_valueerror(self):
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(self.vol, P((3, 3, 3), (3, 3, 3), (3, 3, 3)))

    # Checks that projecting onto a one-voxel volume does not crash or create an invalid value.
    def test_one_voxel_volume(self):
        v = pp.load_nrrd(os.path.join(SYN, "tiny_u8_1x1x1.nrrd"))
        E = pp.project(v, P((0, 0, 0), (0, 0, 5), (0, 5, 0), (0, 5, 5)))   # must not crash
        self.assertLessEqual(int(E.max()), 7)

    # Checks for many random triangles that sampled voxels remain within the expected distance of the plane.
    def test_property_random_planes_lie_on_the_plane(self):
        """Every non-zero pixel must come from a voxel within 0.5*sqrt(3) of the plane."""
        rnd = random.Random(1)
        shape, tol = self.vol.shape, 0.5 * 3 ** 0.5 + 1e-6
        checked = 0
        for _ in range(40):
            a = np.array([rnd.uniform(0, 39), rnd.uniform(0, 29), rnd.uniform(0, 19)])
            d = np.array([rnd.uniform(-1, 1) for _ in range(3)]); d *= rnd.uniform(8, 25) / np.linalg.norm(d)
            side = np.cross(d, [0.3, 0.5, 0.8]); side *= rnd.uniform(4, 15) / np.linalg.norm(side)
            b, c = a + d + side, a + d - side                      # |ab| == |ac|
            E = quiet(pp.project, self.vol, P(a, b, c))
            n = np.cross(b - a, c - a); n /= np.linalg.norm(n)
            for v in np.unique(E[E > 0]):
                x, rest = int(v) % shape[0], int(v) // shape[0]
                q = np.array([x, rest % shape[1], rest // shape[1]], float)
                self.assertLessEqual(abs(np.dot(n, q - a)), tol)
                checked += 1
        self.assertGreater(checked, 500)


# --------------------------------------------------------------- end-to-end
def read_video_frames(path):
    """Decode all frames with imageio (None if unavailable). The ResourceWarning raised inside
    imageio's ffmpeg generator is third-party noise and is silenced here only."""
    import warnings
    try:
        import imageio.v2 as iio
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            with iio.get_reader(path) as reader:
                return [f for f in reader]
    except Exception:
        return None


def frame_count(path):
    frames = read_video_frames(path)
    if frames is not None:
        return len(frames)
    try:
        import cv2
        return int(cv2.VideoCapture(path).get(cv2.CAP_PROP_FRAME_COUNT))
    except Exception:
        return None


class TestDemoCli(unittest.TestCase):
    """The demo `main`:  python Ex1.py file.nrrd file.csv file.mp4"""

    def run_cli(self, nrrd, csv, out, env=None):
        e = dict(os.environ, **(env or {}))
        return subprocess.run([sys.executable, os.path.join(ROOT, "Ex1.py"), nrrd, csv, out],
                              capture_output=True, text=True, env=e)

    # Runs the CLI on the MRI and demo CSV, then checks that it writes an MP4 with one frame per plane.
    def test_demo_one_frame_per_csv_row(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.mp4")
            r = self.run_cli(MRHEAD, os.path.join(ROOT, "data", "planes_demo.csv"), out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.getsize(out) > 1000)
            n = frame_count(out)
            if n is not None:
                self.assertEqual(n, 5)

    # Runs the CLI with a temporary mixed CSV and checks that invalid rows still get video frames.
    def test_instructor_csv_and_bad_rows_keep_frame_count(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.csv")
            write_file(bad, "hdr\n3,200,200,0,0,200,400,400,200,400,,,\nxx,1\n"
                       "3,5,5,5,5,5,5,5,5,5,,,\n4,200,0,0,200,0,500,200,400,0,200,400,500\n")
            out = os.path.join(d, "o.mp4")
            r = self.run_cli(MRHEAD, bad, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            n = frame_count(out)
            if n is not None:
                self.assertEqual(n, 4)

    # Checks that a missing input file produces a clear error and a failing exit status.
    def test_errors_give_message_and_nonzero_exit(self):
        r = self.run_cli("missing.nrrd", os.path.join(ROOT, "data", "planes_demo.csv"), "x.mp4")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Error", r.stderr)


# ---------------------------------------------------------------- performance
@unittest.skipIf(os.environ.get("EX0_FAST"), "EX0_FAST set")
class TestPerformance(unittest.TestCase):
    def _fps(self, dtype, plane, n=15):
        data = np.random.randint(0, 255, (500, 500, 500)).astype(dtype)
        vol = pp.Volume(data, data.shape)
        pp.project(vol, plane)                          # warm-up
        t = time.perf_counter()
        for _ in range(n):
            pp.project(vol, plane)
        return n / (time.perf_counter() - t)

    # Measures projection speed on generated 500-cubed arrays and checks the minimum 30-fps requirement.
    def test_500_cubed_at_least_30_fps(self):
        oblique = P((250, 0, 0), (100, 499, 499), (400, 499, 499))
        full = P((0, 0, 250), (0, 499, 250), (499, 0, 250), (499, 499, 250))
        for dt in (np.uint8, np.uint16):
            for name, pl in (("oblique", oblique), ("full 499x499", full)):
                fps = self._fps(dt, pl)
                print("\n  500^3 %s %-13s %6.0f fps %s" % (np.dtype(dt).name, name, fps,
                                                          "(>=100 target met)" if fps >= 100 else "(below 100 target)"))
                self.assertGreaterEqual(fps, 30)

# ------------------------------------------- merged-review additions (v2)
class TestRoundingAndInput(unittest.TestCase):
    # Checks scalar rounding, including exact positive and negative halves.
    def test_round_nearest_halves_away_from_zero(self):
        for v, r in [(0.5, 1), (1.5, 2), (2.5, 3), (-0.5, -1), (-1.5, -2), (-2.5, -3), (0.49, 0), (-0.49, 0), (7.0, 7)]:
            self.assertEqual(pp.round_nearest(v), r, v)

    # Checks that NumPy array rounding matches scalar rounding for the same values.
    def test_vectorised_rounding_matches_scalar(self):
        a = np.array([-3.5, -2.5, -1.5, -0.5, -0.49, 0.0, 0.49, 0.5, 1.5, 2.5, 3.5, 1e6 + 0.5, -1e6 - 0.5])
        self.assertEqual(pp.round_nearest_array(a).tolist(), [pp.round_nearest(float(v)) for v in a])

    # Checks that an NRRD header with Windows-style CRLF line endings is parsed correctly.
    def test_crlf_nrrd_header(self):
        raw = ("NRRD0004\r\ntype: uchar\r\ndimension: 3\r\nsizes: 2 2 1\r\nencoding: raw\r\n\r\n").encode() + bytes([1, 2, 3, 4])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "crlf.nrrd")
            write_file(p, raw, "wb")
            v = pp.load_nrrd(p)
        self.assertEqual(v.shape, (2, 2, 1))
        self.assertEqual(int(v.data[1, 0, 0]) if np is not None else v.data[1], 2)

    # Checks that NaN, infinity, invalid point counts, and missing coordinates are rejected in CSV rows.
    def test_nonfinite_and_malformed_csv_rows_rejected(self):
        hdr = "n,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        rows = ["3,nan,0,0,1,1,1,2,2,2,,,", "3,inf,0,0,1,1,1,2,2,2,,,", "3.5,0,0,0,1,1,1,2,2,2,,,",
                "3,0,0,0,1,1,1,2,2,,,,", "4,0,0,0,1,1,1,2,2,2,,,", "5,0,0,0,1,1,1,2,2,2,3,3,3"]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bad.csv")
            write_file(p, hdr + "\n".join(rows) + "\n")
            planes = quiet(pp.load_planes, p)
        self.assertEqual(planes, [None] * 6)

    # Checks that an excessively large plane is rejected before a huge output image is allocated.
    def test_oversized_plane_is_rejected_not_allocated(self):
        v = pp.load_nrrd(os.path.join(SYN, "tiny_u8_1x1x1.nrrd"))
        with self.assertRaises(ValueError):
            pp.project(v, P((0, 0, 0), (0, 1e7, 0), (1e7, 0, 0), (1e7, 1e7, 0)))

    # Checks the trapezoid base-length rule: a wider starting base is rejected, but equal bases are allowed.
    def test_trapezoid_with_wider_start_than_end_raises(self):
        """Q&A 1b: dist(a1,a2) <= dist(b,c) is required."""
        vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(vol, P((0, 0, 5), (10, 29, 5), (39, 0, 5), (29, 29, 5)))   # |a1a2|=39 > |bc|=19
        pp.project(vol, P((0, 0, 5), (0, 29, 5), (39, 0, 5), (39, 29, 5)))         # equality is allowed

    # Checks that fractional side lengths still advance rows in unit steps and produce the expected image.
    def test_unit_step_semantics_with_fractional_length(self):
        """Dab is not an integer: rows advance by exactly one unit (assignment), not by Dab/rows."""
        vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        E = pp.project(vol, P((0, 0, 7), (0, 10.4, 7), (30, 0, 7), (30, 10.4, 7)))
        self.assertEqual(E.shape, (11, 30))                                  # loop `y < 10.4` runs 11 times
        self.assertTrue(np.array_equal(E[:, :30], vol.data[:30, 1:12, 7].T))   # y+1 = 1..11 (unit steps)

    # Checks that the CLI reports a clean error for a corrupt NRRD instead of an uncaught traceback.
    def test_cli_corrupt_nrrd_gives_clean_error(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.nrrd")
            write_file(bad, b"NRRD0004\ntype: uchar\ndimension: 3\nsizes: 9 9 9\nencoding: raw\n\nabc", "wb")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "Ex1.py"), bad,
                                os.path.join(ROOT, "data", "planes_demo.csv"), os.path.join(d, "o.mp4")],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        # Judge our program only: its LAST stderr line must be the clean message.
        # (An uncaught exception would end with "ValueError: ..." instead, and
        # unrelated noise written earlier by the environment is ignored.)
        last = [l for l in r.stderr.splitlines() if l.strip()][-1]
        self.assertTrue(last.startswith("Error: ValueError: Invalid NRRD file"), last)

# ------------------------------------- literal assignment pseudo-code (oracle)
def reference_projection(M, a1, b, a2, c):
    """Straight transcription of the instructor's pseudo-code (steps 1-6), plain Python,
    with the documented decisions: round half away from zero, x rounded, out-of-range dropped."""
    sub = lambda p, q: [p[i] - q[i] for i in range(3)]
    norm = lambda v: math.sqrt(sum(t * t for t in v))
    Dab, Dbc = norm(sub(b, a1)), norm(sub(c, b))
    vab = [t / Dab for t in sub(b, a1)]
    vac = [t / norm(sub(c, a2)) for t in sub(c, a2)]
    rows, cols = math.ceil(Dab - 1e-9), math.ceil(Dbc - 1e-9)   # `y < Dab` runs ceil(Dab) times
    E = [[0] * cols for _ in range(rows)]
    p1, p2 = list(a1), list(a2)
    sx, sy, sz = M.shape
    for y in range(rows):                                  # 5. for y
        p1 = [p1[i] + vab[i] for i in range(3)]            # a. a1 = a1 + v(ab)
        p2 = [p2[i] + vac[i] for i in range(3)]            # b. a2 = a2 + v(ac)
        p = list(p1)                                       # c. p = a1
        d12 = norm(sub(p2, p1))                            # d.
        dp = [t / d12 for t in sub(p2, p1)] if d12 > 1e-12 else [0.0] * 3   # e.
        for x1 in range(int(math.floor(d12)) + 1):         # f. for x1 <= d12
            q = [pp.round_nearest(t) for t in p]
            v = M[q[0], q[1], q[2]] if (0 <= q[0] < sx and 0 <= q[1] < sy and 0 <= q[2] < sz) else 0   # i.
            x = pp.round_nearest(Dbc / 2 - d12 / 2 + x1)  # ii.
            if 0 <= x < cols:
                E[y][x] = v                                # iii.
            p = [p[i] + dp[i] for i in range(3)]           # iv.
    return np.array(E, dtype=M.dtype)


class TestAgainstAssignmentPseudoCode(unittest.TestCase):
    def _compare(self, vol, planes):
        for pl in planes:
            ref = reference_projection(vol.data, pl.a1, pl.b, pl.a2, pl.c)
            got = quiet(pp.project, vol, pl)
            self.assertEqual(got.shape, ref.shape)
            self.assertTrue(np.array_equal(got, ref))

    # Compares projections of 30 random valid triangles and trapezoids on the MRI with a simple reference implementation.
    def test_random_isosceles_triangles_and_trapezoids_on_real_mri(self):
        vol = pp.load_nrrd(MRHEAD)
        rnd = np.random.default_rng(11)
        planes = []
        for k in range(30):
            a = np.array([rnd.uniform(-20, 276), rnd.uniform(-20, 276), rnd.uniform(-10, 140)])
            d = rnd.normal(size=3); d *= rnd.uniform(15, 140) / np.linalg.norm(d)
            s = np.cross(d, rnd.normal(size=3)); s *= rnd.uniform(8, 110) / np.linalg.norm(s)
            if k % 2 == 0:                                    # triangle a, a+d+s, a+d-s
                planes.append(pp.Plane(tuple(a), tuple(a + d + s), tuple(a), tuple(a + d - s)))
            else:                                             # trapezoid a', b, a'', c  (a'' = a' + t)
                t = s * rnd.uniform(0.1, 0.9)
                planes.append(pp.Plane(tuple(a), tuple(a + d), tuple(a + t), tuple(a + t + d)))
        self._compare(vol, planes)

    # Compares valid instructor CSV rows 1, 2, and 4 on the MRI against the reference implementation.
    def test_instructor_csv_rows_1_2_4(self):
        vol = pp.load_nrrd(MRHEAD)
        pls = quiet(pp.load_planes, os.path.join(ROOT, "data", "planes_instructor.csv"))
        self._compare(vol, [pls[0], pls[1], pls[3]])           # row 3 is deliberately not isosceles

    # Checks that instructor CSV row 3 is rejected while the other selected rows are valid.
    def test_instructor_csv_row3_is_the_invalid_one(self):
        """Row 3 of the instructor's file (|ab|=497.4 vs |ac|=476.9) must be rejected, the others accepted."""
        vol = pp.load_nrrd(MRHEAD)
        pls = quiet(pp.load_planes, os.path.join(ROOT, "data", "planes_instructor.csv"))
        for k in (0, 1, 3):
            pp.project(vol, pls[k])
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(vol, pls[2])

    # Compares projections across the four synthetic index volumes and their different data types with the reference.
    def test_all_dtypes_on_index_volumes(self):
        for name in ("index_u8_raw_15x16x1.nrrd", "index_u16_gzip_40x30x20.nrrd",
                     "index_u32_gzip_be_50x60x70.nrrd", "index_i16_raw_20x20x20.nrrd"):
            vol = pp.load_nrrd(os.path.join(SYN, name))
            sx, sy, sz = vol.shape
            a = (sx / 2.0, sy / 2.0, 1.0)                      # isosceles: b = a+d+s, c = a+d-s
            d, s = (0.0, 0.0, sz - 3.0), (sx / 2.0 - 2.0, sy / 3.0, 0.0)
            pl = pp.Plane(a, tuple(a[i] + d[i] + s[i] for i in range(3)), a, tuple(a[i] + d[i] - s[i] for i in range(3)))
            self._compare(vol, [pl])

    # Checks that trapezoid points must be coplanar within the EPS tolerance.
    def test_coplanarity_is_enforced_with_eps(self):
        """Q&A 1c: a1->b and a2->c must be on one plane (tolerance EPS)."""
        vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(vol, P((0, 0, 5), (0, 20, 5), (30, 0, 5), (30, 20, 15)))        # 10 voxels off
        with self.assertRaises(pp.InvalidPlaneError):
            pp.project(vol, P((0, 0, 5), (0, 20, 5), (30, 0, 5), (30, 20, 5.01)))      # 0.01 > EPS
        pp.project(vol, P((0, 0, 5), (0, 20, 5), (30, 0, 5), (30, 20, 5.0004)))        # 0.0004 < EPS

    # Checks that collinear triangle and trapezoid points are rejected.
    def test_collinear_points_are_invalid(self):
        vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        for pts in (((5, 5, 5), (5, 5, 15), (5, 5, -5)),                       # triangle a,b,c on one line
                    ((0, 0, 5), (0, 10, 5), (0, 20, 5), (0, 30, 5))):          # trapezoid a1,b,a2 collinear
            with self.assertRaises(pp.InvalidPlaneError):
                pp.project(vol, P(*pts))


class TestInvalidPlanesProduceErrorFrames(unittest.TestCase):
    """Instructor Q&A 3: invalid set -> exception; the demo video gets an error frame for it."""

    # Checks the error-frame size, visible markings, mostly black background, plane label, and tiny-image handling.
    def test_error_frame_has_marking_and_is_mostly_black(self):
        f = pp.make_error_frame(100, 160, 3)
        self.assertEqual(f.shape, (100, 160))
        self.assertTrue(f.any())                                  # marking present
        self.assertGreater((f == 0).mean(), 0.7)                  # still a "black" frame
        self.assertFalse(np.array_equal(f, pp.make_error_frame(100, 160, 4)))   # different number -> different marking
        pp.make_error_frame(2, 2, 1)                             # tiny sizes must not crash

    # Checks that the CLI keeps valid frames correct and inserts marked error frames for invalid CSV rows.
    def test_cli_valid_planes_stay_correct_next_to_invalid_ones(self):
        with tempfile.TemporaryDirectory() as d:
            csvp = os.path.join(d, "mixed.csv")
            write_file(csvp, "hdr\n"
                       "3,200,200,0,0,200,400,400,200,400,,,\n"        # valid
                       "3,200,200,-30,-50,200,400,400,250,400,,,\n"    # not isosceles -> error frame
                       "abc,1,2\n"                                       # malformed -> error frame
                       "4,0,0,5,10,29,5,39,0,5,29,29,5\n"               # |a1a2| > |bc| -> error frame
                       "4,200,0,0,200,0,500,200,400,0,200,400,500\n")   # valid
            out = os.path.join(d, "o.mp4")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "Ex1.py"), MRHEAD, csvp, out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.count("error frame written"), 3)
            self.assertIn("5 frame(s) (2 valid, 3 error)", r.stdout)
            n = frame_count(out)
            if n is not None:
                self.assertEqual(n, 5)                                # one frame per CSV row
            frames = read_video_frames(out)
            if frames is None:
                return
            gray = [f[:, :, 0].astype(float) for f in frames]
            for k in (1, 2, 3):                                       # error frames: border is white
                self.assertGreater(gray[k][0, :].mean(), 200)
                self.assertGreater(gray[k][:, 0].mean(), 200)
            for k in (0, 4):                                          # valid frames: not an error frame
                self.assertLess(gray[k][0, :].mean(), 100)
            self.assertGreater(abs(gray[1] - gray[2]).sum(), 0)       # numbers differ


class TestReviewFindings(unittest.TestCase):
    """Cases raised in an independent review of the code."""

    # Checks a valid edge-case plane against an image calculated by hand.
    def test_valid_plane_with_a2_on_segment_a1b_hand_computed(self):
        """a1=(0,0,0) b=(2,0,0) a2=(1,0,0) c=(1,2,0): all Q&A rules hold (|a1b|=|a2c|=2, |a1a2|=1 <= |bc|=sqrt5,
        coplanar) although a1,b,a2 are collinear. Expected image derived BY HAND from the pseudo-code:
          rows = ceil(2) = 2, cols = ceil(sqrt5) = 3, M[x,y,z] = x + 3*y
          y=0: a1=(1,0,0) a2=(1,1,0) d12=1  dp=(0,1,0)  x = round(sqrt5/2 - 1/2 + x1) = 1, 2 -> M[1,0,0]=1, M[1,1,0]=4
          y=1: a1=(2,0,0) a2=(1,2,0) d12=sqrt5 dp=(-1,2,0)/sqrt5  x = x1 = 0,1,2
               points (2,0,0), (1.55,0.89,0)->(2,1,0), (1.11,1.79,0)->(1,2,0) -> 2, 5, 7"""
        data = np.array([[[x + 3 * y] for y in range(3)] for x in range(3)], dtype=np.uint16)   # shape (3,3,1)
        vol = pp.Volume(data, data.shape)
        pl = pp.Plane((0, 0, 0), (2, 0, 0), (1, 0, 0), (1, 2, 0))
        expected = np.array([[0, 1, 4], [2, 5, 7]], dtype=np.uint16)
        self.assertTrue(np.array_equal(pp.project(vol, pl), expected))

    # Checks that tiny floating-point error does not add an extra projected row.
    def test_rows_are_not_inflated_by_float_noise(self):
        """True length 7, math.dist gives 7.000000000000001: the loop `y < 7` runs 7 times, not 8."""
        a, b = (21.6, 38.1, 0.1), (25.8, 43.7, 0.1)
        self.assertGreater(math.dist(a, b), 7.0)                     # the float noise really exists
        pl = pp.Plane(a, b, (22.6, 38.1, 0.1), (26.8, 43.7, 0.1))
        _, _, rows, cols, _ = pp.plane_geometry(pl)
        self.assertEqual((rows, cols), (7, 1))

    # Checks 300 tie-heavy planes for duplicate output columns and agreement with the reference algorithm.
    def test_no_duplicate_write_columns_and_equals_pseudo_code(self):
        """Tie-heavy planes (half-integer offsets, negative coordinates): no two samples of a row share a
        destination column, so the NumPy scatter is deterministic and equals the literal pseudo-code transcription."""
        vol = pp.load_nrrd(os.path.join(SYN, "index_u16_gzip_40x30x20.nrrd"))
        rnd = random.Random(5)
        checked = 0
        for _ in range(300):
            a = [rnd.randint(-8, 30) / 2.0, rnd.randint(-8, 20) / 2.0, rnd.randint(0, 38) / 2.0]
            L, W = rnd.randint(3, 18), rnd.randint(2, 30)
            w0 = rnd.randint(0, W)
            pl = pp.Plane(tuple(a), (a[0], a[1] + L, a[2]), (a[0] + w0, a[1], a[2]), (a[0] + w0 + (W - w0) * 0, a[1] + L, a[2]))
            pl = pp.Plane(tuple(a), (a[0], a[1] + L, a[2]), (a[0] + W / 2.0, a[1], a[2]), (a[0] + W / 2.0, a[1] + L, a[2]))
            step1, step2, rows, cols, dbc = pp.plane_geometry(pl)
            for y in range(rows):
                a1 = [pl.a1[i] + (y + 1) * step1[i] for i in range(3)]
                a2 = [pl.a2[i] + (y + 1) * step2[i] for i in range(3)]
                d12 = math.dist(a1, a2)
                xs = [pp.round_nearest(dbc / 2.0 - d12 / 2.0 + x1) for x1 in range(int(math.floor(d12)) + 1)]
                self.assertEqual(len(xs), len(set(xs)))
            self.assertTrue(np.array_equal(pp.project(vol, pl),
                                           reference_projection(vol.data, pl.a1, pl.b, pl.a2, pl.c)))
            checked += 1
        self.assertEqual(checked, 300)


class TestCsvExtraFields(unittest.TestCase):
    """A row must hold exactly N points: extra non-empty values are an error, empty padding is fine."""

    def _load(self, rows):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "p.csv")
            write_file(p, "hdr\n" + "\n".join(rows) + "\n")
            return quiet(pp.load_planes, p)

    # Checks that a CSV row declaring three points is rejected when extra point coordinates are present.
    def test_n3_with_extra_points_is_invalid(self):
        planes = self._load(["3,200,200,0,0,200,400,400,200,400,9,9,9",            # a 4th point with N=3
                             "3,200,200,0,0,200,400,400,200,400,1,2,3,4,5,6"])      # two extra points
        self.assertEqual(planes, [None, None])

    # Checks that a CSV row declaring four points is rejected when a fifth point is present.
    def test_n4_with_a_fifth_point_is_invalid(self):
        self.assertEqual(self._load(["4,200,0,0,200,0,500,200,400,0,200,400,500,7,7,7"]), [None])

    # Checks that optional trailing CSV cells are accepted when they are empty.
    def test_empty_padding_is_still_valid(self):
        planes = self._load(["3,200,200,0,0,200,400,400,200,400,,,",
                             "3,200,200,0,0,200,400,400,200,400",
                             "4,200,0,0,200,0,500,200,400,0,200,400,500,,"])
        self.assertTrue(all(p is not None for p in planes))

    # Checks that the CLI makes error frames for rows with extra points while keeping the valid row.
    def test_cli_gives_error_frames_for_rows_with_extra_points(self):
        with tempfile.TemporaryDirectory() as d:
            csvp = os.path.join(d, "x.csv")
            write_file(csvp, "hdr\n3,200,200,0,0,200,400,400,200,400,9,9,9\n"
                             "3,200,200,0,0,200,400,400,200,400,,,\n"
                             "4,200,0,0,200,0,500,200,400,0,200,400,500,7,7,7\n")
            out = os.path.join(d, "o.mp4")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "Ex1.py"), MRHEAD, csvp, out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("3 frame(s) (1 valid, 2 error)", r.stdout)



class TestDefaultFileDiscovery(unittest.TestCase):
    """The no-argument default must never pick a detached-header .nhdr file
    (detached data files are not supported by the reader)."""

    # Checks that automatic input discovery chooses an .nrrd file instead of a detached .nhdr header.
    def test_nhdr_is_not_auto_selected(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("a.nhdr", "b.nrrd", "c.csv"):
                open(os.path.join(d, name), "w").close()
            import plane_projection.cli as cli
            old = cli.project_dir
            cli.project_dir = lambda: d
            try:
                got = cli.find_in_project((".nrrd",), "NRRD")
            finally:
                cli.project_dir = old
            self.assertEqual(os.path.basename(got), "b.nrrd")


class TestClassDataset(unittest.TestCase):
    """The data set shared by the class (data/class_dataset): every plane of every CSV must be valid
    (the CSV files were written for the lecturer's rules) and must give a non-empty image."""
    CASES = [("onion", "class_dataset/onion.nrrd", 120), ("biscuit_cake", "class_dataset/biscuit_cake.nrrd", 120),
             ("swiss_roll", "class_dataset/swiss_roll.nrrd", 120), ("croissant", "class_dataset/croissant.nrrd", 100),
             ("head", "MRHead_1.nrrd", 280)]

    # Checks every available class-dataset CSV plane for validity and a nonempty projection.
    def test_every_plane_is_valid_and_not_empty(self):
        for name, nrrd_file, count in self.CASES:
            with self.subTest(name):
                path = os.path.join(ROOT, "data", nrrd_file)
                if not os.path.exists(path):          # croissant.nrrd (63 MB) is not stored in the repository
                    self.skipTest("%s is missing - copy it from the class folder to data/class_dataset/" % nrrd_file)
                vol = pp.load_nrrd(path)
                planes = pp.load_planes(os.path.join(ROOT, "data", "class_dataset", "csv", name + ".csv"))
                self.assertEqual(len(planes), count)
                for number, pl in enumerate(planes, start=1):
                    self.assertIsNotNone(pl, "CSV row %d is invalid" % number)
                    self.assertTrue(pp.project(vol, pl).any(), "plane %d is empty" % number)

    # Runs the CLI on the class onion volume and checks that all 120 CSV rows produce valid frames.
    def test_cli_gives_one_frame_per_row(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.mp4")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "Ex1.py"),
                                os.path.join(ROOT, "data", "class_dataset", "onion.nrrd"),
                                os.path.join(ROOT, "data", "class_dataset", "csv", "onion.csv"), out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Wrote 120 frame(s) (120 valid, 0 error)", r.stdout)


if __name__ == "__main__":
    unittest.main()
