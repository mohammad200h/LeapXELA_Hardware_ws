#!/usr/bin/env python3
"""Launch test: perturb flex_uspa46_3_0 and verify /hand_sensors response."""

import time
import unittest

import launch
import launch_ros.actions
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from xela_sparshskin_sim.msg import HandSensors, TaxelPertubation


FLEX_VERTEX_ID = "flex_uspa46_3_0"
EXPECTED_TAXEL_ID = 328
APPLIED_FORCE = [0.0, 0.0, -1.5]


@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    sim_node = launch_ros.actions.Node(
        package="xela_sparshskin_sim",
        executable="process_hand_sensors_into_pointcloud",
        name="process_hand_sensors_into_pointcloud",
        output="screen",
        parameters=[{"render_hz": 30, "joint_topic": "xela_joint_publisher"}],
    )
    return (
        launch.LaunchDescription(
            [
                sim_node,
                launch_testing.actions.ReadyToTest(),
            ]
        ),
        {"sim_node": sim_node},
    )


class TestFlexUspa463Perturbation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_flex_uspa46_3_perturbation")
        self.latest_hand_sensors = None
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub = self.node.create_subscription(
            HandSensors, "hand_sensors", self._on_hand_sensors, qos
        )
        self.pub = self.node.create_publisher(TaxelPertubation, "taxel_perturbation", qos)

    def tearDown(self):
        self.node.destroy_node()

    def _on_hand_sensors(self, msg: HandSensors):
        self.latest_hand_sensors = msg

    def _spin_until(self, predicate, timeout_sec: float, description: str):
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return
        self.fail(f"Timed out waiting for: {description}")

    def _find_texel(self, msg: HandSensors):
        for texel in msg.texels:
            if texel.sensor_name == FLEX_VERTEX_ID:
                return texel
        return None

    def test_force_increases_and_taxel_id(self):
        # Wait until the sim is publishing the full taxel set.
        self._spin_until(
            lambda: (
                self.latest_hand_sensors is not None
                and self._find_texel(self.latest_hand_sensors) is not None
            ),
            timeout_sec=30.0,
            description=f"/hand_sensors containing {FLEX_VERTEX_ID}",
        )

        baseline = self._find_texel(self.latest_hand_sensors)
        self.assertIsNotNone(baseline)
        self.assertEqual(
            baseline.taxel_id,
            EXPECTED_TAXEL_ID,
            f"{FLEX_VERTEX_ID} taxel_id={baseline.taxel_id}, expected {EXPECTED_TAXEL_ID}",
        )
        baseline_mag = (baseline.fx**2 + baseline.fy**2 + baseline.fz**2) ** 0.5

        pert = TaxelPertubation()
        pert.flex_vertex_id = FLEX_VERTEX_ID
        pert.taxel_id = EXPECTED_TAXEL_ID
        pert.force = list(APPLIED_FORCE)

        # Publish continuously for a short window so the sim applies xfrc and republishes.
        end = time.time() + 2.0
        while time.time() < end:
            self.pub.publish(pert)
            rclpy.spin_once(self.node, timeout_sec=0.02)
            time.sleep(0.02)

        self._spin_until(
            lambda: (
                self.latest_hand_sensors is not None
                and self._find_texel(self.latest_hand_sensors) is not None
                and (
                    (
                        self._find_texel(self.latest_hand_sensors).fx ** 2
                        + self._find_texel(self.latest_hand_sensors).fy ** 2
                        + self._find_texel(self.latest_hand_sensors).fz ** 2
                    )
                    ** 0.5
                    > baseline_mag + 0.1
                )
            ),
            timeout_sec=10.0,
            description=f"force magnitude on {FLEX_VERTEX_ID} to increase",
        )

        after = self._find_texel(self.latest_hand_sensors)
        self.assertIsNotNone(after)
        self.assertEqual(after.taxel_id, EXPECTED_TAXEL_ID)
        self.assertEqual(after.sensor_name, FLEX_VERTEX_ID)
        after_mag = (after.fx**2 + after.fy**2 + after.fz**2) ** 0.5
        self.assertGreater(
            after_mag,
            baseline_mag + 0.1,
            f"force did not increase: baseline={baseline_mag:.4f} after={after_mag:.4f} "
            f"(fx,fy,fz)=({after.fx}, {after.fy}, {after.fz})",
        )
        # Perturbations are interpreted in the taxel-local frame, so the world
        # direction depends on the flex vertex pose. Magnitude should still rise.
