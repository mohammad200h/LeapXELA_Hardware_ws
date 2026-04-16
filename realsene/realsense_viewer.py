#!/usr/bin/env python3

import sys


def main() -> int:
    try:
        import pyrealsense2 as rs
    except Exception as e:
        print(
            "Failed to import pyrealsense2. Install librealsense Python bindings.\n"
            f"Error: {e}",
            file=sys.stderr,
        )
        return 1

    try:
        import cv2
        import numpy as np
    except Exception as e:
        print(f"Failed to import OpenCV/numpy: {e}", file=sys.stderr)
        return 1

    pipeline = rs.pipeline()
    config = rs.config()

    # D435i supports both color + depth. If your camera differs, adjust these.
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    align_to = rs.stream.color
    align = rs.align(align_to)
    colorizer = rs.colorizer()

    try:
        pipeline.start(config)
    except Exception as e:
        print(f"Failed to start RealSense pipeline: {e}", file=sys.stderr)
        return 1

    try:
        while True:
            frames = pipeline.wait_for_frames()
            frames = align.process(frames)

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if not color_frame or not depth_frame:
                continue

            color = np.asanyarray(color_frame.get_data())
            depth_color = np.asanyarray(colorizer.colorize(depth_frame).get_data())

            stacked = np.hstack((color, depth_color))
            cv2.imshow("RealSense (color | depth)", stacked)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # q or ESC
                break
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import pyrealsense2 as rs
import numpy as np
import cv2
import time

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()

# Start streaming from the default RealSense camera
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start pipeline
pipeline.start(config)
time.sleep(2)  # Give camera time to initialize

try:
    while True:
        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Apply colormap to depth image for visualization
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03),
                                           cv2.COLORMAP_JET)

        # Stack both images horizontally
        images = np.hstack((color_image, depth_colormap))

        # Show images
        cv2.imshow('RealSense Stream (Color | Depth)', images)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Stop streaming
    pipeline.stop()
    cv2.destroyAllWindows()