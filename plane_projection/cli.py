# =============================================================================
# FILE OVERVIEW
# Command-line interface. It reads command-line options, locates input files, runs each plane projection, prepares video frames, and writes the output video.
# =============================================================================

import argparse
import math
import os
import sys
import time
import zlib

from plane_projection.csv_reader import load_planes
from plane_projection.imaging import make_error_frame, pad_gray, to_gray
from plane_projection.nrrd_reader import load_nrrd
from plane_projection.projection import project
from plane_projection.video import write_video



# =============================================================================
# EXPLANATION
# Returns the project folder path. It starts from this module file and goes up to its parent project directory.
# Code follows below.
# =============================================================================

def project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



# =============================================================================
# EXPLANATION
# Finds the first matching file in the project folder, sorted by filename. If none is found it stops with a helpful message; if several are found it reports which one it chose.
# Code follows below.
# =============================================================================

def find_in_project(exts, what):
    folder = project_dir()
    found = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(exts) and not f.lower().endswith("_output.csv")
                   and os.path.isfile(os.path.join(folder, f)))
    if not found:
        sys.exit("No %s file found in the project folder:\n  %s\n"
                 "Put it there, or run: python Ex1.py file.nrrd file.csv file.mp4"
                 % (what, folder))
    if len(found) > 1:
        print("[info] several %s files found, using '%s' (others: %s)"
              % (what, found[0], ", ".join(found[1:])))
    return os.path.join(folder, found[0])



# =============================================================================
# EXPLANATION
# Runs the main workflow: parses options, checks the frame rate, loads the NRRD volume and CSV planes, projects valid planes, builds matching valid or error frames, and writes the video.
# Code follows below.
# =============================================================================

def _run(argv=None):
    ap = argparse.ArgumentParser(
        description="Project a 3D NRRD volume onto the planes listed in a CSV file "
                    "and write one video frame per plane.")
    ap.add_argument("nrrd", nargs="?", help="input 3D volume (.nrrd); default: first .nrrd in the project folder")
    ap.add_argument("csv", nargs="?", help="input planes (.csv); default: first .csv in the project folder")
    ap.add_argument("mp4", nargs="?", help="output video (.mp4); default: <csv name>_output.mp4")
    ap.add_argument("--fps", type=float, default=1.0,
                    help="video frame rate (default 1: each plane shown for 1s)")
    args = ap.parse_args(argv)
    if not math.isfinite(args.fps) or args.fps <= 0:
        ap.error("--fps must be a positive finite number")

    if not args.nrrd:
        args.nrrd = find_in_project((".nrrd",), "NRRD")
    if not args.csv:
        args.csv = find_in_project((".csv",), "CSV")
    if not args.mp4:
        args.mp4 = os.path.splitext(args.csv)[0] + "_output.mp4"
    print("NRRD: %s\nCSV : %s" % (args.nrrd, args.csv))

    vol = load_nrrd(args.nrrd)
    print("Volume %s" % (vol.shape,))
    planes = load_planes(args.csv)
    if not planes:
        sys.exit("No planes found in " + args.csv)

    images = []
    for number, plane in enumerate(planes, start=1):
        if plane is None:
            images.append(None)
            continue
        start = time.perf_counter()
        try:
            projection = project(vol, plane)
        except ValueError as error:
            print("[warn] plane %d: %s - error frame written" % (number, error), file=sys.stderr)
            images.append(None)
            continue
        seconds = time.perf_counter() - start
        gray = to_gray(projection, vol.vmin, vol.vmax)
        print("plane %d: %dx%d  (%.1f ms, %.1f fps)"
              % (number, gray.shape[1], gray.shape[0], seconds * 1e3, 1.0 / max(seconds, 1e-9)))
        images.append(gray)

    assert len(images) == len(planes)
    valid_images = [img for img in images if img is not None]
    error_count = len(images) - len(valid_images)

    min_height, min_width = (100, 160) if error_count else (1, 1)
    height = max([img.shape[0] for img in valid_images] + [min_height])
    width = max([img.shape[1] for img in valid_images] + [min_width])
    if not valid_images:
        height, width = 256, 256
    height, width = height + height % 2, width + width % 2

    frames = [pad_gray(img, height, width) if img is not None
              else make_error_frame(height, width, number)
              for number, img in enumerate(images, start=1)]
    write_video(frames, args.mp4, args.fps)
    print("Wrote %d frame(s) (%d valid, %d error), %dx%d -> %s"
          % (len(images), len(valid_images), error_count, width, height, args.mp4))



# =============================================================================
# EXPLANATION
# Public command-line entry point. Calls _run and turns common input or file errors into a readable message before exiting.
# Code follows below.
# =============================================================================

def main(argv=None):
    try:
        _run(argv)
    except (OSError, ValueError, KeyError, NotImplementedError, EOFError, zlib.error) as e:
        sys.exit("Error: %s: %s" % (type(e).__name__, e))
