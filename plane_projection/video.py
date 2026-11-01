# =============================================================================
# FILE OVERVIEW
# Writes grayscale frames to an MP4 video.
# =============================================================================

import imageio
import numpy as np


# =============================================================================
# EXPLANATION
# Opens the output video, converts each grayscale frame to three color channels, and adds the frames to the video in order.
# Code follows below.
# =============================================================================
def write_video(frames, path, fps):
    video_writer = imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=2,
    )

    for grayscale_frame in frames:
        # Repeat each pixel value in red, green, and blue to keep the image gray.
        red_channel = grayscale_frame
        green_channel = grayscale_frame
        blue_channel = grayscale_frame

        color_frame = np.stack(
            (red_channel, green_channel, blue_channel),
            axis=-1,
        )

        video_writer.append_data(color_frame)

    video_writer.close()