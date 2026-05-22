import pybullet as p
import numpy as np
import os
import time
from client import QuestHeadsetStreamer


'''
This is based off of https://github.com/Improbable-AI/VisionProTeleop by Younghyo Park et. al. which streams the AVP data.
We then runs inverse kinematics and output LEAP Hand joint angles.
Feed these joint angles into your preferred LEAP Hand API, Python, ROS1/ROS2 etc.

See https://github.com/leap-hand/Bidex_VisionPro_Teleop for further details.

Note how the fingertip positions are matching, but the joint angles between the two hands are not due to the IK solution.  :) 
This is not as accurate as Manus gloves but easier to use.
Inspired by Dexcap https://dex-cap.github.io/ by Wang et. al. and Robotic Telekinesis by Shaw et. al.
'''

# Quest Wi-Fi IPv4 (Settings -> Wi-Fi on headset)
QUEST_IP = "192.168.2.48"

def _decode_pybullet_name(name):
    if isinstance(name, bytes):
        return name.decode("utf-8")
    return name


def get_name_off_ee(robot_id, ee_index):
    """Return the URDF link name for a PyBullet link index (IK end-effector index).

    PyBullet uses -1 for the base link and 0..getNumJoints()-1 for child links;
    link index i is the child link of joint i (see getJointInfo / getLinkState).
    """
    if ee_index == -1:
        return _decode_pybullet_name(p.getBodyInfo(robot_id)[1])
    num_joints = p.getNumJoints(robot_id)
    if ee_index < 0 or ee_index >= num_joints:
        raise ValueError(
            f"Invalid end-effector link index {ee_index} for body {robot_id} "
            f"(valid: -1 or 0..{num_joints - 1})"
        )
    return _decode_pybullet_name(p.getJointInfo(robot_id, ee_index)[12])


def get_ee_index_off_name(robot_id, link_name):
    """Return the PyBullet link index for a URDF link name."""
    if link_name == _decode_pybullet_name(p.getBodyInfo(robot_id)[1]):
        return -1
    for joint_index in range(p.getNumJoints(robot_id)):
        if _decode_pybullet_name(p.getJointInfo(robot_id, joint_index)[12]) == link_name:
            return joint_index
    raise ValueError(f"Link '{link_name}' not found on body {robot_id}")


class Leapv1PybulletIKPython():
    def __init__(self, is_left = False):
        #start AVP         
        self.vps = QuestHeadsetStreamer(quest_ip=QUEST_IP, port=5006)
        # start pybullet
        #clid = p.connect(p.SHARED_MEMORY)
        #clid = p.connect(p.DIRECT)
        p.connect(p.GUI)
        # load right leap hand           
        path_src = os.path.abspath(__file__)
        path_src = os.path.dirname(path_src)
        self.is_left = is_left
        self.glove_to_leap_mapping_scale = 1.6
        

        

        if self.is_left:
            raise ValueError("Left hand is not implemented")
        else:
            path_src =  os.path.join(path_src, "leapXela_right/hand.urdf")
            print(f"Loading LeapXela hand from {path_src}")
            ##You may have to set this path for your setup on ROS2
            self.LeapId = p.loadURDF(
                path_src,
                [-0.12, 0.0, 0.01],
                p.getQuaternionFromEuler([1.57, 0, -1.57]),
                useFixedBase = True
            )

        self.ee_link_names = [
            "if_fingertop_unfied",
            "if_realtip",
            "mf_fingertop_unfied",
            "mf_realtip",
            "rf_fingertop_unfied",
            "rf_realtip",
            "thfingertip_unified",
            "threaltip"          
        ]
        self.leapEndEffectorIndex = [ get_ee_index_off_name(self.LeapId, link_name)  for link_name in self.ee_link_names ]


        
        for ee_index in self.leapEndEffectorIndex:
            name = get_name_off_ee(self.LeapId, ee_index)
            print(f"EE {ee_index} name: {name}")
        
        print("\n\n")
        for link_name in self.ee_link_names:
            ee_index = get_ee_index_off_name(self.LeapId, link_name)
            print(f"EE {ee_index} name: {link_name}")

        self.numJoints = p.getNumJoints(self.LeapId)
        p.setGravity(0, 0, 0)
        useRealTimeSimulation = 0
        p.setRealTimeSimulation(useRealTimeSimulation)
        self.create_target_vis()
            
    def create_target_vis(self):
        # load balls
        small_ball_radius = 0.01
        small_ball_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=small_ball_radius)
        ball_radius = 0.01
        ball_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=ball_radius)
        baseMass = 0.001
        basePosition = [0.25, 0.25, 0]
        
        self.ballMbt = []
        for i in range(0,4):
            self.ballMbt.append(p.createMultiBody(baseMass=baseMass, 
                                baseCollisionShapeIndex=ball_shape, 
                                basePosition=basePosition)
            ) # for base and finger tip joints    
            no_collision_group = 0
            no_collision_mask = 0
            p.setCollisionFilterGroupMask(self.ballMbt[i], -1, no_collision_group, no_collision_mask)
        p.changeVisualShape(self.ballMbt[0], -1, rgbaColor=[1, 0, 0, 1]) 
        p.changeVisualShape(self.ballMbt[1], -1, rgbaColor=[0, 1, 0, 1]) 
        p.changeVisualShape(self.ballMbt[2], -1, rgbaColor=[0, 0, 1, 1])  
        p.changeVisualShape(self.ballMbt[3], -1, rgbaColor=[1, 1, 1, 1])
        
    def update_target_vis(self, hand_pos):
        _, current_orientation = p.getBasePositionAndOrientation( self.ballMbt[0])
        p.resetBasePositionAndOrientation(self.ballMbt[0], hand_pos[3], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[1])
        p.resetBasePositionAndOrientation(self.ballMbt[1], hand_pos[2], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[2])
        p.resetBasePositionAndOrientation(self.ballMbt[2], hand_pos[7], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[3])
        p.resetBasePositionAndOrientation(self.ballMbt[3], hand_pos[1], current_orientation)
        
    def get_glove_data(self, hand_pos):
        #gets the data converts it and then computes IK and visualizes
        # hand_pos[2][0] = hand_pos[2][0] - 0.02  this isn't great because they won't oppose properly
        # hand_pos[3][0] = hand_pos[3][0] - 0.02    
        # hand_pos[6][0] = hand_pos[6][0] + 0.02
        # hand_pos[7][0] = hand_pos[7][0] + 0.02
        #hand_pos[2][1] = hand_pos[2][1] + 0.002
        hand_pos[4][1] = hand_pos[4][1] + 0.002
        hand_pos[6][1] = hand_pos[6][1] + 0.002
        output = self.compute_IK(hand_pos)
        self.update_target_vis(hand_pos)
        return output
    

    def get_avp_data(self):
        #gets the data converts it and then computes IK and visualizes
        r = self.vps.get_latest()              
        if self.is_left:
            hand_pose = np.asarray(r.left.fingers).astype(float)  
        else:
            hand_pose = np.asarray(r['right_fingers']).astype(float) 
        indices = [3,4,8,9,13,14,18,19,23,24]
        hand_pos = hand_pose[indices, :3, 3]
        for i in range(0,10):
            hand_pos[i][0] = hand_pos[i][0] * 1.35 * 1.5
            hand_pos[i][1] = hand_pos[i][1] * 1.5
            hand_pos[i][2] = hand_pos[i][2] * 1.5
        output = self.compute_IK(hand_pos)
        self.update_target_vis(hand_pos)
        return output
        
    def compute_IK(self, hand_pos):
        p.stepSimulation()     

        rightHandIndex_middle_pos = hand_pos[2]
        rightHandIndex_pos = hand_pos[3]
        
        rightHandMiddle_middle_pos = hand_pos[4]
        rightHandMiddle_pos = hand_pos[5]
        
        rightHandRing_middle_pos = hand_pos[6]
        rightHandRing_pos = hand_pos[7]
        
        rightHandThumb_middle_pos = hand_pos[0]
        rightHandThumb_pos = hand_pos[1]
        
        leapEndEffectorPos = [
            rightHandIndex_middle_pos,
            rightHandIndex_pos,
            rightHandMiddle_middle_pos,
            rightHandMiddle_pos,
            rightHandRing_middle_pos,
            rightHandRing_pos,
            rightHandThumb_middle_pos,
            rightHandThumb_pos
        ]

        jointPoses = p.calculateInverseKinematics2(
            self.LeapId,
            self.leapEndEffectorIndex,
            leapEndEffectorPos,
            solver=p.IK_DLS,
            maxNumIterations=50,
            residualThreshold=0.0001,
        )
        
        combined_jointPoses = (jointPoses[0:4] + (0.0,) + jointPoses[4:8] + (0.0,) + jointPoses[8:12] + (0.0,) + jointPoses[12:16] + (0.0,))
        combined_jointPoses = list(combined_jointPoses)

        # update the hand joints
        for i in range(20):
            p.setJointMotorControl2(
                bodyIndex=self.LeapId,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=combined_jointPoses[i],
                targetVelocity=0,
                force=500,
                positionGain=0.3,
                velocityGain=1,
            )

        # map results to real robot
        real_robot_hand_q = np.array([float(0.0) for _ in range(16)])
        #real_left_robot_hand_q = np.array([0.0 for _ in range(16)])

        real_robot_hand_q[0:4] = jointPoses[0:4]
        real_robot_hand_q[4:8] = jointPoses[4:8]
        real_robot_hand_q[8:12] = jointPoses[8:12]
        real_robot_hand_q[12:16] = jointPoses[12:16]
        real_robot_hand_q[0:2] = real_robot_hand_q[0:2][::-1]
        real_robot_hand_q[4:6] = real_robot_hand_q[4:6][::-1]
        real_robot_hand_q[8:10] = real_robot_hand_q[8:10][::-1]
        return [float(i) for i in real_robot_hand_q]

if __name__ == "__main__":
    pbik = Leapv1PybulletIKPython()
    while True:
        output_joints = pbik.get_avp_data()
        print(output_joints)  ##This is the 16 dimensional LEAP Hand vector  Feed this into your python or ROS1/ROS2 code.  Ordering is the same!
        time.sleep(0.03)