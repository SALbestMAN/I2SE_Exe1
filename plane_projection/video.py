# =============================================================================
# FILE OVERVIEW
# Writes grayscale frames to an MP4 video.
# =============================================================================

import imageio
import numpy as np



# =============================================================================
# EXPLANATION
# Opens a video writer for path and appends each grayscale frame as a three-channel frame, using the requested frames per second.
# Code follows below.
# =============================================================================

def write_video(frames, path, fps):
    with imageio.get_writer(path, fps=fps, codec="libx264",
                            pixelformat="yuv420p", macro_block_size=2) as writer:
        for frame in frames:
            writer.append_data(np.stack([frame, frame, frame], axis=-1))
