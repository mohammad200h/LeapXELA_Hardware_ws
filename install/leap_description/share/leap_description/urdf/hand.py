from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string
    from .finger import generate_finger, joint_urdf as finger_joint_urdf, link_urdf as finger_link_urdf
    from .thumb import generate_thumb, joint_urdf as thumb_joint_urdf, link_urdf as thumb_link_urdf
    from .palm import get_palm_constant
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string
    from finger import generate_finger, joint_urdf as finger_joint_urdf, link_urdf as finger_link_urdf
    from thumb import generate_thumb, joint_urdf as thumb_joint_urdf, link_urdf as thumb_link_urdf
    from palm import get_palm_constant

def base_world_xml():
    return f""" <link name="base"/>
  <joint name="base_to_base" type="fixed">
    <parent link="base"/>
    <child link="palm_lower"/>
    <origin rpy="0 0 0" xyz="0 0 0"/>
  </joint>
"""

class BasePalmJoint:
    def joint_type(self) -> str:
        return "revolute"

    def parent_link_name(self) -> str:
        return "palm_lower"

    def axis(self) -> list[float]:
        return [0, 0, -1]


class RFMCPJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "rf_mcp"

    def child_link_name(self) -> str:
        return "rf_mcp"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.0070952454426398371343, -0.067842243865100515521, -0.018722407666402932774],
         "rpy": [1.5707963267948950037, 1.5707963267948945596, 0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.314, "upper": 2.23}


class MFMCPJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "mf_mcp"

    def child_link_name(self) -> str:
        return "mf_mcp"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.0070952496528625388569, -0.022392243865100525113, -0.018722403578460229678],
         "rpy": [1.570796326794896558, 1.570796326794896558, 0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.314, "upper": 2.23}


class IFMCPJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "if_mcp"

    def child_link_name(self) -> str:
        return "if_mcp"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.0070952496528625457958, 0.023057756134899472233, -0.01872240357846021927],
         "rpy": [1.5707963267948950037, 1.5707963267948945596, 0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.314, "upper": 2.23}


class ThumbCMCJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "th_cmc"

    def child_link_name(self) -> str:
        return "cmc"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.069395249652862533996, -0.0012422438651005258004, -0.021622403578460215601],
         "rpy": [-8.2381766464939424156e-17, 1.5707963267948956698, 0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.349, "upper": 2.094}



def generate_mf_rf_if_links_and_joints() -> tuple[str, str]:
    rf_finger = generate_finger("rf", 0.0)
    mf_finger = generate_finger("mf", 0.0)
    if_finger = generate_finger("if", 0.0)

    fingers = [rf_finger, mf_finger, if_finger]

    fingers_links = "\n".join(finger_link_urdf(link) for finger in fingers for link in finger.links)
    joints_urdf = "\n".join(finger_joint_urdf(joint) for finger in fingers for joint in finger.joints)

    return fingers_links, joints_urdf

def generate_thumb_links_and_joints() -> tuple[str, str]:
    thumb = generate_thumb()
    thumb_links = "\n".join(thumb_link_urdf(link) for link in thumb.links)
    thumb_joints = "\n".join(thumb_joint_urdf(joint) for joint in thumb.joints)
    return thumb_links, thumb_joints

def joint_urdf(joint: Any) -> str:
    limit = joint.limit()
    origin = joint.origin()
    return f"""
  <joint name="{joint.joint_name()}" type="{joint.joint_type()}">
    <origin xyz="{list_to_string(origin["xyz"])}" rpy="{list_to_string(origin["rpy"])}"/>
    <parent link="{joint.parent_link_name()}"/>
    <child link="{joint.child_link_name()}"/>
    <axis xyz="{list_to_string(joint.axis())}"/>
    <limit effort="{limit["effort"]}" velocity="{limit["velocity"]}" lower="{limit["lower"]}" upper="{limit["upper"]}"/>
  </joint>
""".rstrip("\n")

def generate_palm_joints() -> str:
    palm_joints = [IFMCPJoint(),MFMCPJoint(), RFMCPJoint(), ThumbCMCJoint()]
    return "\n".join(joint_urdf(j) for j in palm_joints)

def render_hand_joints_urdf() -> str:
    fingers_links, finger_joints = generate_mf_rf_if_links_and_joints()
    thumb_links, thumb_joints = generate_thumb_links_and_joints()
    palm_link = get_palm_constant()
    palm_joints = generate_palm_joints()
    return f"""
  <?xml version="1.0" ?>
  <robot name="xela_palm_generated">
  {base_world_xml()}
  {palm_link}
  {fingers_links}
  {thumb_links}
  {thumb_joints}
  {finger_joints}
  {palm_joints}

  </robot>
  """.rstrip("\n")

def write_hand_urdf(file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(render_hand_joints_urdf())


if __name__ == "__main__":
    import os

    out_path = os.environ.get("OUT") or "hand.urdf"
    write_hand_urdf(out_path)

