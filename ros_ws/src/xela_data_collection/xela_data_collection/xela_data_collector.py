#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image

import numpy as np

from leap_hand.srv import LeapState
from sensor_msgs.msg import JointState


class XelaDataCollector(Node):
    """
    Subscribes to:
      - /leap_image (published by xela_image_publisher)
      - /leap_image_normalized (published by xela_image_publisher)

    If message_filters is available, uses approximate time synchronization and
    calls a single paired callback. Otherwise, falls back to two independent
    subscriptions and logs reception.
    """

    def __init__(self):
        super().__init__("xela_data_collector")

        self._last_raw: Image | None = None
        self._last_norm: Image | None = None
        self._last_state: JointState | None = None
        # Prefer synchronized callbacks when possible
        try:
            from message_filters import Subscriber, ApproximateTimeSynchronizer

            self._raw_sub = Subscriber(self, Image, "/leap_image")
            self._norm_sub = Subscriber(self, Image, "/leap_image_normalized")
            self._state_sub = Subscriber(self, JointState, "/leap_state")
            # Reasonable defaults for two topics at ~same rate
            self._sync = ApproximateTimeSynchronizer(
                [self._raw_sub, self._norm_sub, self._state_sub],
                queue_size=30,
                slop=0.05,
                allow_headerless=False,
            )
            self._sync.registerCallback(self._on_synced_images)
            self.get_logger().info("Using approximate time sync for image topics.")
        except Exception as e:
            self.get_logger().warn(
                f"message_filters not available (or failed to init): {e}. "
                "Falling back to independent subscriptions."
            )
            self._sub_raw = self.create_subscription(Image, "/leap_image", self._on_raw, 10)
            self._sub_norm = self.create_subscription(
                Image, "/leap_image_normalized", self._on_norm, 10
            )
            self._state_sub = self.create_subscription(JointState, "/leap_state", self._on_state, 10)
        self.cli = self.create_client(LeapState, "/leap_state")
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
    


    def get_state(self):
        self.req = LeapState.Request()
        self.future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def _decode_image(self, msg: Image, *, dtype: np.dtype) -> np.ndarray:
        # Publisher uses 3 channels and packs raw bytes.
        h, w = int(msg.height), int(msg.width)
        arr = np.frombuffer(msg.data, dtype=dtype)

        expected = h * w * 3
        if arr.size != expected:
            raise ValueError(
                f"Unexpected image buffer size: got {arr.size}, expected {expected} "
                f"(h={h}, w={w}, channels=3, dtype={dtype})."
            )
        return arr.reshape((h, w, 3))

    def _on_synced_images(self, raw_msg: Image, norm_msg: Image, state_msg: JointState):
        self._last_raw = raw_msg
        self._last_norm = norm_msg
        self._last_state = state_msg
        # Note: xela_image_publisher sets encoding "32FC3" for both topics, but
        # /leap_image is currently filled from an int32 array. We decode raw as int32
        # and normalized as float32 to match the actual byte content.
        try:
            raw = self._decode_image(raw_msg, dtype=np.int32)
            norm = self._decode_image(norm_msg, dtype=np.float32)
        except Exception as e:
            self.get_logger().error(f"Failed to decode images: {e}")
            return

        # self.get_logger().info(
        #     f"Synced images: raw[{raw.shape}] norm[{norm.shape}] "
        #     f"t_raw={raw_msg.header.stamp.sec}.{raw_msg.header.stamp.nanosec:09d} "
        #     f"t_norm={norm_msg.header.stamp.sec}.{norm_msg.header.stamp.nanosec:09d}"
        #     f"t_state={state_msg.header.stamp.sec}.{state_msg.header.stamp.nanosec:09d}"
        # )
        self.get_logger().info(f"Hand state::position {state_msg.position} ")
        # TODO: store data

    def _on_raw(self, msg: Image):
        self._last_raw = msg
        self.get_logger().debug(
            f"Raw image received: {msg.height}x{msg.width} enc={msg.encoding}"
        )

    def _on_norm(self, msg: Image):
        self._last_norm = msg
        self.get_logger().debug(
            f"Normalized image received: {msg.height}x{msg.width} enc={msg.encoding}"
        )

    def _on_state(self, msg: JointState):
        self._last_state = msg
        self.get_logger().debug(f"Hand state received: {msg.position} {msg.velocity} {msg.effort}")


def main(args=None):
    rclpy.init(args=args)
    node = XelaDataCollector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

