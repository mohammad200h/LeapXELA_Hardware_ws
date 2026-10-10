#!/usr/bin/env python3

import json
import os
import numpy as np
import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from threading import RLock
from typing import Any

from ament_index_python.packages import get_package_share_directory

from leap_hand_utils.dynamixel_client import DynamixelClient
import leap_hand_utils.leap_hand_utils as lhu
from leap_hand.srv import LeapPosition, LeapVelocity, LeapEffort, LeapState
from base import LeapXelaBase


def load_joint_config() -> dict[str, Any]:
    """
    Load the joint config JSON from the installed `xela_description` package.
    """
    resolved_path = os.path.join(
        get_package_share_directory("xela_description"),
        "joint_config.json",
    )
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(
            f"Expected joint config at '{resolved_path}', but it does not exist. "
            "Make sure the 'xela_description' package is installed and contains joint_config.json."
        )

    with open(resolved_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_joint_names(joint_config: dict[str, Any]) -> list[str]:
    map = joint_config["leapXela"]["hardware"]["map"]
    joint_names = []
    idx = []

    for finger in ["th", "if", "mf", "rf"]:
        for key, value in map[finger].items():
            idx.append(int(key))
            joint_names.append(f"{finger}_{value}")

    print(f"get_joint_names:: joint_names: {joint_names} \n idx: {idx}")
    print(f"get_joint_names:: joint_names::len:: {len(joint_names)} \n idx::len {len(idx)}")
    return joint_names, idx





def clamp_the_joint_commands(joint_commands):
    # TODO implement this function
    pass

class LeapXELANode(Node):
    def __init__(self):
        super().__init__('leaphand_node')

        joint_config = load_joint_config()
        self.joint_names, self.idx = get_joint_names(joint_config)

        # Guards all reads/writes to the hand hardware so they never overlap.
        self._hw_mutex = RLock()

        # Creates services that can give information about the hand out
        self.create_service(LeapPosition, 'leap_position', self.pos_srv)
        self.create_service(LeapVelocity, 'leap_velocity', self.vel_srv)
        self.create_service(LeapEffort, 'leap_effort', self.eff_srv)
        self.create_service(LeapState, 'leap_state', self.state_srv)

        # Compliant mode: low gains and the goal follows the hand when it is pushed,
        # so the fingers can be posed by hand (kinesthetic teaching).
        self.compliant = self.declare_parameter('compliant', False).value
        self.compliant_deadband = self.declare_parameter('compliant_deadband', 0.05).value
        # While cmd_xela is streaming the commander owns the goal (e.g. a held finger); following
        # the hand then would fight it and make the finger oscillate.
        self.compliant_cmd_timeout = self.declare_parameter('compliant_cmd_timeout', 0.5).value
        self._last_cmd_time = None
        kP = self.declare_parameter('compliant_kP', 60.0).value
        kD = self.declare_parameter('compliant_kD', 40.0).value
        curr_lim = self.declare_parameter('compliant_curr_lim', 120.0).value
        self._compliant_gains = {'kP': float(kP), 'kD': float(kD), 'curr_lim': float(curr_lim)}
        # In compliant mode the joints named in stiff_joints (comma-separated, e.g. the fingers
        # a commander is playing back or holding) use the stiff_* gains so they track the
        # commands; the other joints keep the compliant gains.
        self._stiff_gains = {
            'kP': float(self.declare_parameter('stiff_kP', 600.0).value),
            'kD': float(self.declare_parameter('stiff_kD', 200.0).value),
            'curr_lim': float(self.declare_parameter('stiff_curr_lim', 550.0).value),
        }
        self._motor_of = dict(zip(self.joint_names, self.idx))
        self._stiff_motors: set[int] = set()
        stiff_joints = self.declare_parameter('stiff_joints', '').value
        motors = self._parse_stiff_joints(stiff_joints)
        if isinstance(motors, str):
            raise ValueError(motors)
        self._stiff_motors = motors
        if self.compliant:
            self._leapXela = LeapXelaBase(kP=kP, kI=0, kD=kD, curr_lim=curr_lim)
            with self._hw_mutex:
                self._goal = self._leapXela.dxl_client.read_pos().copy()
                self._leapXela.set_joints_radians(self._goal)
            if self._stiff_motors:
                self._apply_gains()
            self.get_logger().info('Compliant mode: fingers can be moved by hand')
        else:
            self._leapXela = LeapXelaBase()
        # compliant_* can be changed at runtime (e.g. from record_demonstration's Settings tab).
        self.add_on_set_parameters_callback(self._on_set_parameters)
        self.create_subscription(JointState, 'cmd_xela', self._receive_pose, 10)

        self.pub = self.create_publisher(JointState, 'leap_state', 10)
        self.timer = self.create_timer(0.1, self.publish_state)

    def publish_state(self):
        with self._hw_mutex:
            # pos, vel, cur = self._leapXela.dxl_client.read_pos_vel_cur()
            pos = self._leapXela.dxl_client.read_pos()
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()

            msg.name = self.joint_names
            msg.position = pos.tolist()
            # msg.velocity = vel.tolist()
            # msg.effort = cur.tolist()
            self.pub.publish(msg)

            if self.compliant and not self._commanded_recently():
                # The deadband keeps gravity sag from slowly dragging the goal down.
                pushed = np.abs(pos - self._goal) > self.compliant_deadband
                if pushed.any():
                    self._goal[pushed] = pos[pushed]
                    self._leapXela.set_joints_radians(self._goal)

    def _commanded_recently(self):
        if self._last_cmd_time is None:
            return False
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
        return elapsed < self.compliant_cmd_timeout

    def _parse_stiff_joints(self, text):
        """Motor ids of the comma-separated joint names in ``text``, or an error message."""
        names = [n.strip() for n in str(text).split(',') if n.strip()]
        unknown = [n for n in names if n not in self._motor_of]
        if unknown:
            return f"unknown joints in stiff_joints: {', '.join(unknown)}"
        return {self._motor_of[n] for n in names}

    def _apply_gains(self):
        """Compliant gains on the motors not in stiff_joints, stiff gains on the others."""
        if not self.compliant:
            return
        base = self._leapXela
        compliant = [m for m in base.motors if m not in self._stiff_motors]
        stiff = [m for m in base.motors if m in self._stiff_motors]
        c, s = self._compliant_gains, self._stiff_gains
        with self._hw_mutex:
            base.set_motor_gains(compliant, c['kP'], 0, c['kD'], c['curr_lim'])
            base.set_motor_gains(stiff, s['kP'], 0, s['kD'], s['curr_lim'])
        base.kP, base.kD, base.curr_lim = c['kP'], c['kD'], c['curr_lim']

    def _on_set_parameters(self, params):
        values = {p.name: p.value for p in params}
        if 'compliant' in values and values['compliant'] != self.compliant:
            return SetParametersResult(successful=False, reason="'compliant' is fixed at startup")
        gain_names = {
            'compliant_kP': (self._compliant_gains, 'kP'),
            'compliant_kD': (self._compliant_gains, 'kD'),
            'compliant_curr_lim': (self._compliant_gains, 'curr_lim'),
            'stiff_kP': (self._stiff_gains, 'kP'),
            'stiff_kD': (self._stiff_gains, 'kD'),
            'stiff_curr_lim': (self._stiff_gains, 'curr_lim'),
        }
        gains = gain_names.keys() & values.keys()
        if gains and not self.compliant:
            return SetParametersResult(
                successful=False, reason='compliant mode is off; restart with compliant:=true'
            )
        for name, value in values.items():
            if name.startswith(('compliant_', 'stiff_')) and name != 'stiff_joints' and (
                not isinstance(value, (int, float)) or value < 0
            ):
                return SetParametersResult(successful=False, reason=f'{name} must be >= 0')
        stiff_motors = self._stiff_motors
        if 'stiff_joints' in values:
            stiff_motors = self._parse_stiff_joints(values['stiff_joints'])
            if isinstance(stiff_motors, str):
                return SetParametersResult(successful=False, reason=stiff_motors)
        if 'compliant_deadband' in values:
            self.compliant_deadband = float(values['compliant_deadband'])
        if 'compliant_cmd_timeout' in values:
            self.compliant_cmd_timeout = float(values['compliant_cmd_timeout'])
        if not gains and stiff_motors == self._stiff_motors:
            return SetParametersResult(successful=True)
        old = ({**self._compliant_gains}, {**self._stiff_gains}, self._stiff_motors)
        for name in gains:
            group, key = gain_names[name]
            group[key] = float(values[name])
        self._stiff_motors = stiff_motors
        try:
            self._apply_gains()
        except Exception as e:
            self._compliant_gains.update(old[0])
            self._stiff_gains.update(old[1])
            self._stiff_motors = old[2]
            return SetParametersResult(successful=False, reason=f'writing gains failed: {e}')
        if gains:
            c, s = self._compliant_gains, self._stiff_gains
            self.get_logger().info(
                f"Compliant gains: kP={c['kP']:g} kD={c['kD']:g} curr_lim={c['curr_lim']:g}; "
                f"stiff gains: kP={s['kP']:g} kD={s['kD']:g} curr_lim={s['curr_lim']:g}"
            )
        if stiff_motors != old[2]:
            names = [n for n, m in self._motor_of.items() if m in stiff_motors]
            self.get_logger().info(f"Stiff joints: {', '.join(names) or '(none)'}")
        return SetParametersResult(successful=True)

    # Receive LEAP pose and directly control the robot
    def _receive_pose(self, msg):
        pose = msg.position
       
        self.curr_pos = np.array(pose)
        
        with self._hw_mutex:
            if self.compliant:
                self._goal = self.curr_pos.astype(float).copy()
                self._last_cmd_time = self.get_clock().now()
            # self._leapXela.set_joints_degrees(self.curr_pos)
            self._leapXela.set_joints_radians(self.curr_pos)

    # Service that reads and returns the pos of the robot in regular LEAP Embodiment scaling.
    def pos_srv(self, request, response):
        with self._hw_mutex:
            response.position = self._leapXela.dxl_client.read_pos().tolist()
        return response

    # Service that reads and returns the vel of the robot in LEAP Embodiment
    def vel_srv(self, request, response):
        with self._hw_mutex:
            response.velocity = self._leapXela.dxl_client.read_vel().tolist()
        return response

    # Service that reads and returns the effort/current of the robot in LEAP Embodiment
    def eff_srv(self, request, response):
        with self._hw_mutex:
            response.effort = self._leapXela.dxl_client.read_cur().tolist()
        return response

    def state_srv(self, request, response):
        with self._hw_mutex:
            pos, vel, cur = self._leapXela.dxl_client.read_pos_vel_cur()

        response.position = pos.tolist()
        response.velocity = vel.tolist()
        response.effort = cur.tolist()
        return response


    def safe_disconnect(self):
        self._leapXela.safe_disconnect()

    def destroy_node(self):
        self.safe_disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    leaphand_node = LeapXELANode()
    try:
        rclpy.spin(leaphand_node)
    finally:
        leaphand_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
