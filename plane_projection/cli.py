# =============================================================================
# FILE OVERVIEW
# Reads command-line options, loads the input files, creates one image for each plane, and saves the images as a video.
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
# Returns the main project folder by starting at this file and moving up two folders.
# Code follows below.
# =============================================================================
def project_dir():
    this_file = os.path.abspath(__file__)
    package_folder = os.path.dirname(this_file)
    main_folder = os.path.dirname(package_folder)
    return main_folder


# =============================================================================
# EXPLANATION
# Finds the first file with one of the requested extensions in the project folder. If there are several, it chooses the first alphabetically.
# Code follows below.
# =============================================================================
def find_in_project(extensions, file_description):
    folder = project_dir()
    matching_files = []

    # Check every item in the project folder.
    for file_name in os.listdir(folder):
        file_path = os.path.join(folder, file_name)

        # Keep regular files with the requested extension.
        has_requested_extension = file_name.lower().endswith(extensions)
        is_output_csv = file_name.lower().endswith("_output.csv")
        is_regular_file = os.path.isfile(file_path)

        if has_requested_extension and not is_output_csv and is_regular_file:
            matching_files.append(file_name)

    # Sort names so the same file is chosen each time.
    matching_files.sort()

    if len(matching_files) == 0:
        sys.exit(
            "No %s file found in the project folder:\n  %s\n"
            "Put it there, or run: python Ex1.py file.nrrd file.csv file.mp4"
            % (file_description, folder)
        )

    if len(matching_files) > 1:
        chosen_file = matching_files[0]
        other_files = ", ".join(matching_files[1:])

        print(
            "[info] several %s files found, using '%s' (others: %s)"
            % (file_description, chosen_file, other_files)
        )

    return os.path.join(folder, matching_files[0])


# =============================================================================
# EXPLANATION
# Runs the program: reads the options, loads the volume and planes, creates an image for each plane, and writes all images to a video.
# Code follows below.
# =============================================================================
def _run(argv=None):
    # Describe the input options that can be supplied when starting the program.
    argument_parser = argparse.ArgumentParser(
        description=(
            "Project a 3D NRRD volume onto the planes listed in a CSV file "
            "and write one video frame per plane."
        )
    )

    argument_parser.add_argument(
        "nrrd",
        nargs="?",
        help="input 3D volume (.nrrd); default: first .nrrd in the project folder",
    )
    argument_parser.add_argument(
        "csv",
        nargs="?",
        help="input planes (.csv); default: first .csv in the project folder",
    )
    argument_parser.add_argument(
        "mp4",
        nargs="?",
        help="output video (.mp4); default: <csv name>_output.mp4",
    )
    argument_parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="video frame rate (default 1: each plane shown for 1s)",
    )

    # Read the options supplied by the user.
    args = argument_parser.parse_args(argv)

    # The video frame rate must be a real number greater than zero.
    if not math.isfinite(args.fps) or args.fps <= 0:
        argument_parser.error("--fps must be a positive finite number")

    # If no input path was supplied, find an input file in the project folder.
    if not args.nrrd:
        args.nrrd = find_in_project((".nrrd",), "NRRD")

    if not args.csv:
        args.csv = find_in_project((".csv",), "CSV")

    # If no output path was supplied, make one based on the CSV filename.
    if not args.mp4:
        csv_name_without_extension = os.path.splitext(args.csv)[0]
        args.mp4 = csv_name_without_extension + "_output.mp4"

    print("NRRD: %s\nCSV : %s" % (args.nrrd, args.csv))

    # Load the 3D volume and the plane descriptions.
    volume = load_nrrd(args.nrrd)
    print("Volume %s" % (volume.shape,))

    planes = load_planes(args.csv)

    if len(planes) == 0:
        sys.exit("No planes found in " + args.csv)

    # Store one result for each plane. Failed planes are stored as None.
    images = []

    for plane_number, plane in enumerate(planes, start=1):
        # A None value means this plane's CSV row was invalid.
        if plane is None:
            images.append(None)
            continue

        # Measure how long it takes to project this plane.
        start_time = time.perf_counter()

        try:
            projection_image = project(volume, plane)

        except ValueError as error:
            print(
                "[warn] plane %d: %s - error frame written"
                % (plane_number, error),
                file=sys.stderr,
            )
            images.append(None)
            continue

        elapsed_seconds = time.perf_counter() - start_time

        # Convert the projection values to grayscale pixels.
        grayscale_image = to_gray(
            projection_image,
            volume.vmin,
            volume.vmax,
        )

        image_height, image_width = grayscale_image.shape
        frames_per_second_for_this_plane = 1.0 / max(elapsed_seconds, 1e-9)

        print(
            "plane %d: %dx%d  (%.1f ms, %.1f fps)"
            % (
                plane_number,
                image_width,
                image_height,
                elapsed_seconds * 1000,
                frames_per_second_for_this_plane,
            )
        )

        images.append(grayscale_image)

    # Keep the image list aligned with the plane list.
    assert len(images) == len(planes)

    # Count how many planes produced images and how many failed.
    valid_images = []

    for image in images:
        if image is not None:
            valid_images.append(image)

    error_count = len(images) - len(valid_images)

    # Choose the largest image dimensions so every video frame can have one size.
    if error_count > 0:
        minimum_height = 100
        minimum_width = 160
    else:
        minimum_height = 1
        minimum_width = 1

    image_heights = [image.shape[0] for image in valid_images]
    image_widths = [image.shape[1] for image in valid_images]

    height = max(image_heights + [minimum_height])
    width = max(image_widths + [minimum_width])

    # If every plane failed, use a visible default frame size.
    if len(valid_images) == 0:
        height = 256
        width = 256

    # Make both dimensions even, as expected by the chosen video format.
    if height % 2 != 0:
        height += 1

    if width % 2 != 0:
        width += 1

    # Prepare video frames in the same order as the planes.
    frames = []

    for plane_number, image in enumerate(images, start=1):
        if image is None:
            error_frame = make_error_frame(height, width, plane_number)
            frames.append(error_frame)
        else:
            centered_image = pad_gray(image, height, width)
            frames.append(centered_image)

    # Save the prepared frames as a video.
    write_video(frames, args.mp4, args.fps)

    print(
        "Wrote %d frame(s) (%d valid, %d error), %dx%d -> %s"
        % (
            len(images),
            len(valid_images),
            error_count,
            width,
            height,
            args.mp4,
        )
    )


# =============================================================================
# EXPLANATION
# Public entry point for the command-line program. Runs the workflow and shows common errors as readable messages.
# Code follows below.
# =============================================================================
def main(argv=None):
    try:
        _run(argv)

    except (
        OSError,
        ValueError,
        KeyError,
        NotImplementedError,
        EOFError,
        zlib.error,
    ) as error:
        error_type = type(error).__name__
        sys.exit("Error: %s: %s" % (error_type, error))