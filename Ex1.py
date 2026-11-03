#!/usr/bin/env python3
import argparse
import csv
import math
import os
import sys
import time
import zlib
from dataclasses import dataclass

try:
    import imageio
    import nrrd
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as error:
    sys.exit(
        "Missing library '%s'. Install the requirements with:\n"
        "    pip install -r requirements.txt" % error.name
    )


# =============================================================================
# EXPLANATION
# Stores the 3D volume data, its dimensions, and its smallest and largest values.
# Code follows below.
# =============================================================================
class Volume:
    def __init__(self, data, shape):
        self.data = data
        self.shape = shape
        self.minimum_value = float(data.min())
        self.maximum_value = float(data.max())


# =============================================================================
# EXPLANATION
# Reads a NRRD file, checks that it contains valid 3D data, and returns it as a Volume.
# Code follows below.
# =============================================================================
def load_nrrd(file_path):
    try:
        volume_data, _header = nrrd.read(file_path)
    except nrrd.NRRDError as error:
        raise ValueError("Invalid NRRD file: %s" % error) from error

    if volume_data.ndim != 3 or min(volume_data.shape) <= 0:
        raise ValueError(
            "NRRD volume must be 3D with positive sizes (got shape %s)"
            % (volume_data.shape,)
        )

    contiguous_data = np.ascontiguousarray(volume_data)
    return Volume(contiguous_data, contiguous_data.shape)


@dataclass
# =============================================================================
# EXPLANATION
# Stores the four 3D points that describe a triangle or trapezoid.
# Code follows below.
# =============================================================================
class Plane:
    a1: tuple
    b: tuple
    a2: tuple
    c: tuple


# =============================================================================
# EXPLANATION
# Reads the CSV rows and turns each valid row into a Plane. Invalid rows are kept in place.
# Code follows below.
# =============================================================================
def load_planes(file_path):
    with open(file_path, newline="", encoding="utf-8-sig") as csv_file:
        all_rows = list(csv.reader(csv_file))

    data_rows = all_rows[1:]
    planes = []

    for line_number, cells in enumerate(data_rows, start=2):
        cleaned_cells = [cell.strip() for cell in cells]

        if not any(cleaned_cells):
            continue

        try:
            planes.append(_parse_plane(cleaned_cells))
        except ValueError:
            print(
                "[warn] CSV line %d is invalid - error frame written" % line_number,
                file=sys.stderr,
            )
            planes.append(None)

    return planes


# =============================================================================
# EXPLANATION
# Checks one CSV row and turns its coordinate values into a Plane.
# Code follows below.
# =============================================================================
def _parse_plane(cells):
    point_count = float(cells[0])

    if not math.isfinite(point_count) or point_count not in (3.0, 4.0):
        raise ValueError("the number of points must be 3 or 4")

    point_count = int(point_count)
    required_cell_count = 1 + 3 * point_count
    coordinate_cells = cells[1:required_cell_count]

    if len(cells) < required_cell_count:
        raise ValueError("missing coordinates")

    if any(cell == "" for cell in coordinate_cells):
        raise ValueError("missing coordinates")

    if any(cells[required_cell_count:]):
        raise ValueError("too many values")

    coordinates = [float(cell) for cell in coordinate_cells]

    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("coordinates must be finite numbers")

    points = [
        tuple(coordinates[index : index + 3]) for index in range(0, len(coordinates), 3)
    ]

    if point_count == 3:
        point_a, point_b, point_c = points
        return Plane(point_a, point_b, point_a, point_c)

    point_a1, point_b, point_a2, point_c = points
    return Plane(point_a1, point_b, point_a2, point_c)


MAX_SIDE = 4096
EPS = 0.001


# =============================================================================
# EXPLANATION
# Rounds one number to the nearest integer, sending exact halves away from zero.
# Code follows below.
# =============================================================================
def round_nearest(value):
    if value >= 0:
        return int(math.floor(value + 0.5))

    return int(math.ceil(value - 0.5))


# =============================================================================
# EXPLANATION
# Applies the same rounding rule to every number in a NumPy array.
# Code follows below.
# =============================================================================
def _round_array_nearest(values):
    rounded_values = np.floor(values + 0.5)

    if values.min() < 0:
        negative_half_values = (values < 0) & (rounded_values == values + 0.5)
        rounded_values -= negative_half_values

    return rounded_values.astype(np.int64)


# =============================================================================
# EXPLANATION
# Marks an error caused by plane points that do not form valid geometry.
# Code follows below.
# =============================================================================
class InvalidPlaneError(ValueError):
    pass


# =============================================================================
# EXPLANATION
# Finds the direction from one 3D point to another.
# Code follows below.
# =============================================================================
def _vector_between(point_a, point_b):
    return [point_b[axis] - point_a[axis] for axis in range(3)]


# =============================================================================
# EXPLANATION
# Calculates the length of a vector.
# Code follows below.
# =============================================================================
def _vector_length(vector):
    return math.sqrt(sum(component * component for component in vector))


# =============================================================================
# EXPLANATION
# Finds a vector perpendicular to both input vectors.
# Code follows below.
# =============================================================================
def _cross_product(vector_a, vector_b):
    return (
        vector_a[1] * vector_b[2] - vector_a[2] * vector_b[1],
        vector_a[2] * vector_b[0] - vector_a[0] * vector_b[2],
        vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0],
    )


# =============================================================================
# EXPLANATION
# Checks the plane points and calculates the directions and image size needed for projection.
# Code follows below.
# =============================================================================
def _plane_geometry(plane):
    side_a1_to_b = _vector_between(plane.a1, plane.b)
    side_a2_to_c = _vector_between(plane.a2, plane.c)

    length_a1_to_b = math.dist(plane.a1, plane.b)
    length_a2_to_c = math.dist(plane.a2, plane.c)
    length_b_to_c = math.dist(plane.b, plane.c)
    length_a1_to_a2 = _vector_length(_vector_between(plane.a1, plane.a2))

    if min(length_a1_to_b, length_a2_to_c, length_b_to_c) <= 1e-12:
        raise InvalidPlaneError("degenerate plane (coincident points)")

    side_length_difference = abs(length_a1_to_b - length_a2_to_c)

    if side_length_difference >= EPS:
        raise InvalidPlaneError(
            "|dist(a1,b) - dist(a2,c)| = %.4f is not < EPS (%g): not isosceles"
            % (side_length_difference, EPS)
        )

    if length_a1_to_a2 > 1e-12:
        if length_a1_to_a2 > length_b_to_c + 1e-9:
            raise InvalidPlaneError(
                "dist(a1,a2) = %.4f exceeds dist(b,c) = %.4f"
                % (length_a1_to_a2, length_b_to_c)
            )

        _check_four_points_on_one_plane(
            plane,
            longest_side=max(
                length_a1_to_b,
                length_b_to_c,
                length_a1_to_a2,
            ),
        )
    else:
        normal_vector = _cross_product(side_a1_to_b, side_a2_to_c)

        if _vector_length(normal_vector) <= (1e-9 * length_a1_to_b * length_a2_to_c):
            raise InvalidPlaneError("degenerate plane (a, b, c are collinear)")

    row_count = math.ceil(length_a1_to_b - 1e-9)
    column_count = math.ceil(length_b_to_c - 1e-9)

    if row_count > MAX_SIDE or column_count > MAX_SIDE:
        raise ValueError(
            "Plane too large (%dx%d, limit %d)" % (row_count, column_count, MAX_SIDE)
        )

    direction_a1_to_b = [component / length_a1_to_b for component in side_a1_to_b]
    direction_a2_to_c = [component / length_a2_to_c for component in side_a2_to_c]

    return (
        direction_a1_to_b,
        direction_a2_to_c,
        row_count,
        column_count,
        length_b_to_c,
    )


# =============================================================================
# EXPLANATION
# Checks that all four points lie on the same plane within the allowed tolerance.
# Code follows below.
# =============================================================================
def _check_four_points_on_one_plane(plane, longest_side):
    points = (plane.a1, plane.b, plane.a2, plane.c)

    possible_point_groups = (
        (0, 1, 2, 3),
        (0, 1, 3, 2),
        (0, 2, 3, 1),
        (1, 2, 3, 0),
    )

    largest_normal_length = None
    largest_normal = None
    origin_point_index = None
    remaining_point_index = None

    for (
        first_index,
        second_index,
        third_index,
        remaining_index,
    ) in possible_point_groups:
        vector_1 = _vector_between(points[first_index], points[second_index])
        vector_2 = _vector_between(points[first_index], points[third_index])
        normal_vector = _cross_product(vector_1, vector_2)
        normal_length = _vector_length(normal_vector)

        if largest_normal_length is None or normal_length > largest_normal_length:
            largest_normal_length = normal_length
            largest_normal = normal_vector
            origin_point_index = first_index
            remaining_point_index = remaining_index

    if largest_normal_length <= 1e-9 * longest_side**2:
        raise InvalidPlaneError("degenerate plane (all 4 points are collinear)")

    vector_to_remaining_point = _vector_between(
        points[origin_point_index],
        points[remaining_point_index],
    )

    distance_from_plane = (
        abs(
            sum(
                largest_normal[axis] * vector_to_remaining_point[axis]
                for axis in range(3)
            )
        )
        / largest_normal_length
    )

    if distance_from_plane >= EPS:
        raise InvalidPlaneError(
            "the 4 points are not on one plane "
            "(one point is %.4f off the plane of the other three)" % distance_from_plane
        )


# =============================================================================
# EXPLANATION
# Samples the 3D volume along the plane and returns the result as a 2D image.
# Code follows below.
# =============================================================================
def project(volume, plane):
    (
        direction_a1_to_b,
        direction_a2_to_c,
        row_count,
        column_count,
        distance_b_to_c,
    ) = _plane_geometry(plane)

    volume_data = volume.data

    row_numbers = np.arange(
        1,
        row_count + 1,
        dtype=np.float64,
    )[:, np.newaxis]

    left_endpoints = np.array(plane.a1, dtype=np.float64) + row_numbers * np.array(
        direction_a1_to_b
    )
    right_endpoints = np.array(plane.a2, dtype=np.float64) + row_numbers * np.array(
        direction_a2_to_c
    )

    row_directions = right_endpoints - left_endpoints
    row_lengths = np.linalg.norm(row_directions, axis=1)

    unit_directions = np.divide(
        row_directions,
        row_lengths[:, np.newaxis],
        out=np.zeros_like(row_directions),
        where=row_lengths[:, np.newaxis] > 1e-12,
    )

    last_steps = np.floor(row_lengths)

    if last_steps.max() > 2 * MAX_SIDE:
        raise ValueError("Plane too wide (row length %.0f)" % last_steps.max())

    step_numbers = np.arange(
        int(last_steps.max()) + 1,
        dtype=np.float64,
    )[np.newaxis, :]

    image_columns = _round_array_nearest(
        distance_b_to_c / 2.0 - row_lengths[:, np.newaxis] / 2.0 + step_numbers
    )

    valid_samples = (
        (step_numbers <= last_steps[:, np.newaxis])
        & (image_columns >= 0)
        & (image_columns < column_count)
    )

    flat_voxel_indices = None

    for axis, axis_size in enumerate(volume.shape):
        positions = (
            left_endpoints[:, axis][:, np.newaxis]
            + step_numbers * unit_directions[:, axis][:, np.newaxis]
        )
        voxel_indices = _round_array_nearest(positions)

        valid_samples &= (voxel_indices >= 0) & (voxel_indices < axis_size)

        if flat_voxel_indices is None:
            flat_voxel_indices = voxel_indices
        else:
            flat_voxel_indices = flat_voxel_indices * axis_size + voxel_indices

    sampled_values = volume_data.reshape(-1).take(
        flat_voxel_indices,
        mode="clip",
    )

    flat_image_positions = (
        np.arange(row_count, dtype=np.int64)[:, np.newaxis] * column_count
        + image_columns
    )
    flat_image_positions[~valid_samples] = row_count * column_count

    flat_image = np.zeros(
        row_count * column_count + 1,
        dtype=volume_data.dtype,
    )
    flat_image[flat_image_positions] = sampled_values

    return flat_image[: row_count * column_count].reshape(
        row_count,
        column_count,
    )


# =============================================================================
# EXPLANATION
# Converts projection values into grayscale pixels from black to white.
# Code follows below.
# =============================================================================
def to_gray(projection, minimum_value, maximum_value):
    if maximum_value > minimum_value:
        scale = 255.0 / (maximum_value - minimum_value)
    else:
        scale = 0.0

    clipped_values = np.clip(
        projection.astype(np.float32),
        minimum_value,
        maximum_value,
    )

    gray_values = (clipped_values - minimum_value) * scale
    return gray_values.astype(np.uint8)


# =============================================================================
# EXPLANATION
# Centers a grayscale image on a larger black canvas.
# Code follows below.
# =============================================================================
def pad_gray(image, canvas_height, canvas_width):
    image_height, image_width = image.shape
    canvas = np.zeros(
        (canvas_height, canvas_width),
        dtype=np.uint8,
    )

    top = (canvas_height - image_height) // 2
    left = (canvas_width - image_width) // 2

    canvas[
        top : top + image_height,
        left : left + image_width,
    ] = image

    return canvas


# =============================================================================
# EXPLANATION
# Creates a marked image for a plane that could not be processed.
# Code follows below.
# =============================================================================
def make_error_frame(height, width, plane_number):
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)

    draw.line(
        [(0, 0), (width - 1, height - 1)],
        fill=110,
        width=2,
    )
    draw.line(
        [(0, height - 1), (width - 1, 0)],
        fill=110,
        width=2,
    )
    draw.rectangle(
        [0, 0, width - 1, height - 1],
        outline=255,
    )

    label = "PLANE #%d" % plane_number
    font_size = max(
        8,
        min(height // 5, int(width / (0.7 * len(label)))),
    )
    font = ImageFont.load_default(size=font_size)

    draw.text(
        (width / 2, height / 2 - 0.7 * font_size),
        "ERROR",
        fill=255,
        font=font,
        anchor="mm",
    )
    draw.text(
        (width / 2, height / 2 + 0.7 * font_size),
        label,
        fill=255,
        font=font,
        anchor="mm",
    )

    return np.asarray(image)


# =============================================================================
# EXPLANATION
# Saves the image frames in order as an MP4 video.
# Code follows below.
# =============================================================================
def write_video(frames, output_path, frames_per_second):
    with imageio.get_writer(
        output_path,
        fps=frames_per_second,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=2,
    ) as video_writer:
        for grayscale_frame in frames:
            color_frame = np.stack(
                [grayscale_frame, grayscale_frame, grayscale_frame],
                axis=-1,
            )
            video_writer.append_data(color_frame)


# =============================================================================
# EXPLANATION
# Returns the folder containing this script.
# Code follows below.
# =============================================================================
def project_dir():
    return os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# EXPLANATION
# Finds the first matching input file in the project folder.
# Code follows below.
# =============================================================================
def find_in_project(extensions, file_description):
    project_folder = project_dir()

    matching_files = sorted(
        file_name
        for file_name in os.listdir(project_folder)
        if file_name.lower().endswith(extensions)
        and not file_name.lower().endswith("_output.csv")
        and os.path.isfile(os.path.join(project_folder, file_name))
    )

    if not matching_files:
        sys.exit(
            "No %s file found in the project folder:\n  %s\n"
            "Put it there, or run: python Ex1.py file.nrrd file.csv file.mp4"
            % (file_description, project_folder)
        )

    if len(matching_files) > 1:
        print(
            "[info] several %s files found, using '%s' (others: %s)"
            % (
                file_description,
                matching_files[0],
                ", ".join(matching_files[1:]),
            )
        )

    return os.path.join(project_folder, matching_files[0])


# =============================================================================
# EXPLANATION
# Runs the full workflow: load files, project planes, prepare frames, and write the video.
# Code follows below.
# =============================================================================
def _run(arguments=None):
    parser = argparse.ArgumentParser(
        description=(
            "Project a 3D NRRD volume onto the planes listed in a CSV file "
            "and write one video frame per plane."
        )
    )

    parser.add_argument(
        "nrrd",
        nargs="?",
        help="input 3D volume (.nrrd); default: first .nrrd in the project folder",
    )
    parser.add_argument(
        "csv",
        nargs="?",
        help="input planes (.csv); default: first .csv in the project folder",
    )
    parser.add_argument(
        "mp4",
        nargs="?",
        help="output video (.mp4); default: <csv name>_output.mp4",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="video frame rate (default 1: each plane shown for 1s)",
    )

    args = parser.parse_args(arguments)

    if not math.isfinite(args.fps) or args.fps <= 0:
        parser.error("--fps must be a positive finite number")

    if not args.nrrd:
        args.nrrd = find_in_project((".nrrd",), "NRRD")

    if not args.csv:
        args.csv = find_in_project((".csv",), "CSV")

    if not args.mp4:
        csv_name_without_extension = os.path.splitext(args.csv)[0]
        args.mp4 = csv_name_without_extension + "_output.mp4"

    print("NRRD: %s\nCSV : %s" % (args.nrrd, args.csv))

    volume = load_nrrd(args.nrrd)
    print("Volume %s" % (volume.shape,))

    planes = load_planes(args.csv)

    if not planes:
        sys.exit("No planes found in " + args.csv)

    images = []

    for plane_number, plane in enumerate(planes, start=1):
        if plane is None:
            images.append(None)
            continue

        start_time = time.perf_counter()

        try:
            projection = project(volume, plane)
        except ValueError as error:
            print(
                "[warn] plane %d: %s - error frame written" % (plane_number, error),
                file=sys.stderr,
            )
            images.append(None)
            continue

        elapsed_seconds = time.perf_counter() - start_time
        grayscale_image = to_gray(
            projection,
            volume.minimum_value,
            volume.maximum_value,
        )

        image_height, image_width = grayscale_image.shape
        processing_fps = 1.0 / max(elapsed_seconds, 1e-9)

        print(
            "plane %d: %dx%d  (%.1f ms, %.1f fps)"
            % (
                plane_number,
                image_width,
                image_height,
                elapsed_seconds * 1000,
                processing_fps,
            )
        )

        images.append(grayscale_image)

    assert len(images) == len(planes)

    valid_images = [image for image in images if image is not None]
    error_count = len(images) - len(valid_images)

    if error_count:
        minimum_frame_height = 100
        minimum_frame_width = 160
    else:
        minimum_frame_height = 1
        minimum_frame_width = 1

    image_heights = [image.shape[0] for image in valid_images]
    image_widths = [image.shape[1] for image in valid_images]

    frame_height = max(image_heights + [minimum_frame_height])
    frame_width = max(image_widths + [minimum_frame_width])

    if not valid_images:
        frame_height = 256
        frame_width = 256

    if frame_height % 2 != 0:
        frame_height += 1

    if frame_width % 2 != 0:
        frame_width += 1

    video_frames = []

    for plane_number, image in enumerate(images, start=1):
        if image is None:
            frame = make_error_frame(
                frame_height,
                frame_width,
                plane_number,
            )
        else:
            frame = pad_gray(
                image,
                frame_height,
                frame_width,
            )

        video_frames.append(frame)

    write_video(video_frames, args.mp4, args.fps)

    print(
        "Wrote %d frame(s) (%d valid, %d error), %dx%d -> %s"
        % (
            len(images),
            len(valid_images),
            error_count,
            frame_width,
            frame_height,
            args.mp4,
        )
    )


# =============================================================================
# EXPLANATION
# Starts the program and displays common errors as readable messages.
# Code follows below.
# =============================================================================
def main(arguments=None):
    try:
        _run(arguments)
    except (
        OSError,
        ValueError,
        KeyError,
        NotImplementedError,
        EOFError,
        zlib.error,
    ) as error:
        sys.exit("Error: %s: %s" % (type(error).__name__, error))


if __name__ == "__main__":
    main()
