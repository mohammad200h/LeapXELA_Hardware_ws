class BasePalmJoint
    def joint_type
      'revolute'
    end
  
    def parent_link_name
      'leap_hand_xela_back_cover'
    end
  
    def axis
      [0.0, 0.0, 1.0]
    end
  end
  
  class RFPalmJoint < BasePalmJoint
    def joint_name = 'rf_mcp'
    def child_link_name = 'p4_unified'
    def origin = { xyz: [-0.02317, -0.0165, 0.1436], rpy: [3.14159, -1.5708, 0.0] }
    def limit = { effort: 10, velocity: 10, lower: -0.314159, upper: 2.23402 }
  end
  
  class MFPalmJoint < BasePalmJoint
    def joint_name = 'mf_mcp'
    def child_link_name = 'p4_unified_2'
    def origin = { xyz: [0.02228, -0.0165, 0.1436], rpy: [3.14159, -1.5708, 0.0] }
    def limit = { effort: 10, velocity: 10, lower: -0.314159, upper: 2.23402 }
  end
  
  class IFPalmJoint < BasePalmJoint
    def joint_name = 'if_mcp'
    def child_link_name = 'p4_unified_3'
    def origin = { xyz: [0.06773, -0.0165, 0.1436], rpy: [3.14159, -1.5708, 0.0] }
    def limit = { effort: 10, velocity: 10, lower: -0.314159, upper: 2.23402 }
  end
  
  class ThumbPalmJoint < BasePalmJoint
    def joint_name = 'th_cmc'
    def child_link_name = 'thp2_unified'
    def origin = { xyz: [0.0480627, -0.013, 0.07], rpy: [-3.14159, 0.0, 3.14159] }
    def limit = { effort: 10, velocity: 10, lower: -0.349066, upper: 2.0944 }
  end
  
  def joint_urdf(joint)
    limit = joint.limit
    %Q{
    <joint name="#{joint.joint_name}" type="#{joint.joint_type}">
      <origin xyz="#{list_to_string(joint.origin[:xyz])}" rpy="#{list_to_string(joint.origin[:rpy])}"/>
      <parent link="#{joint.parent_link_name}"/>
      <child link="#{joint.child_link_name}"/>
      <axis xyz="#{list_to_string(joint.axis)}"/>
      <limit effort="#{limit[:effort]}" velocity="#{limit[:velocity]}" lower="#{limit[:lower]}" upper="#{limit[:upper]}"/>
    </joint>
    }
  end
  
  def generate_fingers_palm_joints
    [RFPalmJoint.new, MFPalmJoint.new, IFPalmJoint.new, ThumbPalmJoint.new]
  end


  def plam_joints_urdf
    generate_fingers_palm_joints.map { |j| joint_urdf(j) }.join("\n")
  end
  

# Unfinished