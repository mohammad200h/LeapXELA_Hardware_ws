#!/usr/bin/env python3

import json
import os
import sys

import rclpy
from ament_index_python.packages import get_package_share_directory
from arm_server.action import UpdatePlanningScene
from arm_server.msg import SceneObject
from rclpy.action import ActionClient
from rclpy.node import Node


class BuildTheWallNode(Node):
    @staticmethod
    def apply_color(scene_object, color_spec):
        if isinstance(color_spec, list):
            if len(color_spec) not in (3, 4):
                raise ValueError('color list must have 3 or 4 values: [r, g, b] or [r, g, b, a]')
            scene_object.use_color = True
            scene_object.color_r = float(color_spec[0])
            scene_object.color_g = float(color_spec[1])
            scene_object.color_b = float(color_spec[2])
            scene_object.color_a = float(color_spec[3]) if len(color_spec) == 4 else 1.0
            return

        if isinstance(color_spec, dict):
            scene_object.use_color = True
            scene_object.color_r = float(color_spec.get('r', 1.0))
            scene_object.color_g = float(color_spec.get('g', 1.0))
            scene_object.color_b = float(color_spec.get('b', 1.0))
            scene_object.color_a = float(color_spec.get('a', 1.0))
            return

        raise ValueError('color must be a list [r, g, b, a] or dict with r, g, b, a keys')

    def __init__(self):
        super().__init__('build_the_wall')

        default_config = os.path.join(
            get_package_share_directory('arm_server'),
            'script',
            'ws_table.json',
        )
        self.declare_parameter('config_file', default_config)
        self.declare_parameter('clear_existing', True)
        self.declare_parameter('action_name', '/update_planning_scene')

        action_name = self.get_parameter('action_name').get_parameter_value().string_value
        self._action_client = ActionClient(self, UpdatePlanningScene, action_name)

    def load_objects(self):
        config_file = self.get_parameter('config_file').get_parameter_value().string_value
        with open(config_file, 'r', encoding='utf-8') as config:
            data = json.load(config)

        objects = []
        for object_id, spec in data.items():
            scene_object = SceneObject()
            scene_object.id = object_id
            scene_object.shape_type = spec['shape_type']
            scene_object.dimensions = [float(value) for value in spec['dimensions']]
            scene_object.x = float(spec.get('x', 0.0))
            scene_object.y = float(spec.get('y', 0.0))
            scene_object.z = float(spec.get('z', 0.0))
            scene_object.roll = float(spec.get('roll', 0.0))
            scene_object.pitch = float(spec.get('pitch', 0.0))
            scene_object.yaw = float(spec.get('yaw', 0.0))
            if 'color' in spec:
                self.apply_color(scene_object, spec['color'])
            objects.append(scene_object)
        return objects

    def send_goal(self):
        if not self._action_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('UpdatePlanningScene action server not available')
            return False

        goal = UpdatePlanningScene.Goal()
        goal.clear_existing = self.get_parameter('clear_existing').get_parameter_value().bool_value
        goal.objects = self.load_objects()

        config_file = self.get_parameter('config_file').get_parameter_value().string_value
        self.get_logger().info(
            f'Sending {len(goal.objects)} object(s) from {config_file}'
        )

        send_goal_future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        if result.success:
            self.get_logger().info(f'Added {result.objects_added} object(s): {result.message}')
            return True

        self.get_logger().error(result.message)
        return False


def main(args=None):
    rclpy.init(args=args)
    node = BuildTheWallNode()
    try:
        success = node.send_goal()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
