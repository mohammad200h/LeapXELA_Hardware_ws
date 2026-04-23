require 'erb'
require 'matrix'
require_relative 'list_to_string'


class LinkP4
  attr_reader :prefix

  def initialize(prefix)
    @prefix = prefix
  end

  # For now this template generates a single link (p4_unified),
  # matching `xela_description/robot.urdf`.
  def link_name
    "#{prefix}_p4_unified"
  end

  def inertial
    {
      origin: { xyz: [0.0342889, -0.0265621, -0.0145004], rpy: [0.0, 0.0, 0.0] },
      mass: 0.044,
      inertia: {
        ixx: 6.90801e-06,
        ixy: 2.26365e-06,
        ixz: 1.79475e-07,
        iyy: 1.04766e-05,
        iyz: -1.82708e-07,
        izz: 1.10431e-05
      }
    }
  end

  def visual
    {
      origin: { xyz: [0.0048, -0.0, -0.0145], rpy: [1.5708, 1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p4_unified.stl' } },
      material: {
        name: 'p4_unified_material',
        color: { rgba: [0.972549, 0.529412, 0.00392157, 1.0] }
      }
    }
  end

  def collision
    {
      origin: { xyz: [0.0048, -0.0, -0.0145], rpy: [1.5708, 1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p4_unified.stl' } }
    }
  end
end


class LinkP3
  attr_reader :prefix

  def initialize(prefix)
    @prefix = prefix
  end

  def link_name
    "#{prefix}_p3_unified"
  end

  def inertial
    {
      origin: { xyz: [-0.000258994, 0.00848001, 0.0133488], rpy: [0.0, 0.0, 0.0] },
      mass: 0.032,
      inertia: {
        ixx: 3.54425e-06,
        ixy: -1.6457e-08,
        ixz: -1.5221e-08,
        iyy: 2.67248e-06,
        iyz: -1.71388e-07,
        izz: 3.5384e-06
      }
    }
  end

  def visual
    {
      origin: { xyz: [0.0, 0.0075, 0.0], rpy: [-1.5708, -1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p3_unified.stl' } },
      material: {
        name: 'p3_unified_material',
        color: { rgba: [0.972549, 0.529412, 0.00392157, 1.0] }
      }
    }
  end

  def collision
    {
      origin: { xyz: [0.0, 0.0075, 0.0], rpy: [-1.5708, -1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p3_unified.stl' } }
    }
  end
end

class LinkP2
  attr_reader :prefix

  def initialize(prefix)
    @prefix = prefix
  end

  def link_name
    "#{prefix}_p2_unified"
  end

  def inertial
    {
      origin: { xyz: [0.0304899, -0.00688132, -0.0146269], rpy: [0.0, 0.0, 0.0] },
      mass: 0.037,
      inertia: {
        ixx: 8.11059e-06,
        ixy: 5.66349e-07,
        ixz: 1.88699e-07,
        iyy: 6.98155e-06,
        iyz: -9.6344e-08,
        izz: 9.0141e-06
      }
    }
  end

  def visual
    {
      origin: { xyz: [0.00905, -0.0, -0.0145], rpy: [1.5708, 1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p2_unified.stl' } },
      material: {
        name: 'p2_unified_material',
        color: { rgba: [0.768627, 0.886275, 0.952941, 1.0] }
      }
    }
  end

  def collision
    {
      origin: { xyz: [0.00905, -0.0, -0.0145], rpy: [1.5708, 1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/p2_unified.stl' } }
    }
  end
end

class LinkFingertop
  attr_reader :prefix

  def initialize(prefix)
    @prefix = prefix
  end

  def link_name
    "#{prefix}_fingertop_unfied"
  end

  def inertial
    {
      origin: { xyz: [-0.00193531, -0.0359351, 0.0145854], rpy: [0.0, 0.0, 0.0] },
      mass: 0.016,
      inertia: {
        ixx: 1.0779e-05,
        ixy: 1.57487e-07,
        ixz: -2.8587e-08,
        iyy: 5.55855e-06,
        iyz: -1.64744e-07,
        izz: 1.00656e-05
      }
    }
  end

  def visual
    {
      origin: { xyz: [-0.00135925, -0.025, 0.0145], rpy: [-1.5708, -1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/fingertop_unfied.stl' } },
      material: {
        name: 'fingertop_unfied_material',
        color: { rgba: [0.917647, 0.917647, 0.917647, 1.0] }
      }
    }
  end

  def collision
    {
      origin: { xyz: [-0.00135925, -0.025, 0.0145], rpy: [-1.5708, -1.5708, 0.0] },
      geometry: { mesh: { filename: 'package://assets/fingertop_unfied.stl' } }
    }
  end
end

class JointP4P3
  attr_reader :prefix
  attr_reader :offset

  def initialize(prefix, offset)
    @prefix = prefix
    @offset = offset
  end

  def joint_name
    "#{prefix}_rot"
  end

  def joint_type
    'revolute'
  end

  def origin
    { xyz: [0.0326 + offset, -0.0123, -0.0145], rpy: [-1.5708, -1.5708, 0.0] }
  end

  def parent_link_name
    "#{prefix}_p4_unified"
  end

  def child_link_name
    "#{prefix}_p3_unified"
  end

  def axis
    [0.0, 0.0, 1.0]
  end

  def limit
    { effort: 10, velocity: 10, lower: -1.0472, upper: 1.0472 }
  end
end


class JointP3P2
  attr_reader :prefix
  attr_reader :offset

  def initialize(prefix, offset)
    @prefix = prefix
    @offset = offset
  end

  def joint_name
    "#{prefix}_pip"
  end

  def joint_type
    'revolute'
  end

  def origin
    { xyz: [0.0145 + offset, 0.015, 0.013], rpy: [1.5708, 0.0, 1.5708] }
  end

  def parent_link_name
    "#{prefix}_p3_unified"
  end

  def child_link_name
    "#{prefix}_p2_unified"
  end

  def axis
    [0.0, 0.0, 1.0]
  end

  def limit
    { effort: 10, velocity: 10, lower: -0.506145, upper: 1.88496 }
  end
end

class JointP2Fingertop
  attr_reader :prefix
  attr_reader :offset

  def initialize(prefix, offset)
    @prefix = prefix
    @offset = offset
  end

  def joint_name
    "#{prefix}_dip"
  end

  def joint_type
    'revolute'
  end

  def origin
    { xyz: [0.0361 + offset, 0.0, -0.0291], rpy: [0.0, 0.0, 1.5708] }
  end

  def parent_link_name
    "#{prefix}_p2_unified"
  end

  def child_link_name
    "#{prefix}_fingertop_unfied"
  end

  def axis
    [0.0, 0.0, 1.0]
  end

  def limit
    { effort: 10, velocity: 10, lower: -0.366519, upper: 2.04204 }
  end
end


class Finger
  attr_reader :prefix
  attr_reader :links
  attr_reader :joints

  def initialize(prefix, links = [], joints = [])
    @prefix = prefix
    @links = links
    @joints = joints
  end
end

def generate_finger(prefix, offset)
  p4 = LinkP4.new(prefix)
  p3 = LinkP3.new(prefix)
  p2 = LinkP2.new(prefix)
  fingertop = LinkFingertop.new(prefix)

  links = [p4, p3, p2, fingertop]
  joints = [
    JointP4P3.new(prefix, offset),
    JointP3P2.new(prefix, offset),
    JointP2Fingertop.new(prefix, offset)
  ]

  Finger.new(prefix, links, joints)
end

def link_urdf(link)
  inertial = link.inertial
  visual = link.visual
  collision = link.collision

  %Q{
  <link name="#{link.link_name}">
    <inertial>
      <origin xyz="#{list_to_string(inertial[:origin][:xyz])}" rpy="#{list_to_string(inertial[:origin][:rpy])}"/>
      <mass value="#{inertial[:mass]}"/>
      <inertia ixx="#{inertial[:inertia][:ixx]}" ixy="#{inertial[:inertia][:ixy]}" ixz="#{inertial[:inertia][:ixz]}" iyy="#{inertial[:inertia][:iyy]}" iyz="#{inertial[:inertia][:iyz]}" izz="#{inertial[:inertia][:izz]}"/>
    </inertial>
    <visual>
      <origin xyz="#{list_to_string(visual[:origin][:xyz])}" rpy="#{list_to_string(visual[:origin][:rpy])}"/>
      <geometry>
        <mesh filename="#{visual[:geometry][:mesh][:filename]}"/>
      </geometry>
      <material name="#{visual[:material][:name]}">
        <color rgba="#{list_to_string(visual[:material][:color][:rgba])}"/>
      </material>
    </visual>
    <collision>
      <origin xyz="#{list_to_string(collision[:origin][:xyz])}" rpy="#{list_to_string(collision[:origin][:rpy])}"/>
      <geometry>
        <mesh filename="#{collision[:geometry][:mesh][:filename]}"/>
      </geometry>
    </collision>
  </link>
  }
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

def render_finger_urdf(finger)
  links_xml = finger.links.map { |l| link_urdf(l) }.join("\n")
  joints_xml = finger.joints.map { |j| joint_urdf(j) }.join("\n")

  %Q{<?xml version="1.0" ?>
<robot name="xela_finger_generated">
#{links_xml}
#{joints_xml}

<link name="base"/>
<joint name="base" type="fixed">
  <origin xyz="0 0 0.2" rpy="1.57 0 0"/>
  <parent link="base"/>
  <child link="#{finger.links[0].link_name}"/>
</joint>
</robot>
}
end

def write_finger_urdf(file_path, finger)
  File.write(file_path, render_finger_urdf(finger))
end


if __FILE__ == $0
  finger = generate_finger('rf', 0.0)
  out_path = ENV['OUT'] || 'finger.urdf'
  write_finger_urdf(out_path, finger)
  puts "Wrote #{out_path}"
end