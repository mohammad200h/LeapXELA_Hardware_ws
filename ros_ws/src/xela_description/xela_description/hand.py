from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string


class BasePalmJoint:
    def joint_type(self) -> str:
        return "revolute"

    def parent_link_name(self) -> str:
        return "leap_hand_xela_back_cover"

    def axis(self) -> list[float]:
        return [0.0, 0.0, 1.0]


class RFPalmJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "rf_mcp"

    def child_link_name(self) -> str:
        return "p4_unified"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.02317, -0.0165, 0.1436], "rpy": [3.14159, -1.5708, 0.0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 10, "velocity": 10, "lower": -0.314159, "upper": 2.23402}


class MFPalmJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "mf_mcp"

    def child_link_name(self) -> str:
        return "p4_unified_2"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.02228, -0.0165, 0.1436], "rpy": [3.14159, -1.5708, 0.0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 10, "velocity": 10, "lower": -0.314159, "upper": 2.23402}


class IFPalmJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "if_mcp"

    def child_link_name(self) -> str:
        return "p4_unified_3"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.06773, -0.0165, 0.1436], "rpy": [3.14159, -1.5708, 0.0]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 10, "velocity": 10, "lower": -0.314159, "upper": 2.23402}


class ThumbPalmJoint(BasePalmJoint):
    def joint_name(self) -> str:
        return "th_cmc"

    def child_link_name(self) -> str:
        return "thp2_unified"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.0480627, -0.013, 0.07], "rpy": [-3.14159, 0.0, 3.14159]}

    def limit(self) -> dict[str, Any]:
        return {"effort": 10, "velocity": 10, "lower": -0.349066, "upper": 2.0944}



def generate_mf_rf_if_links_and_joints():
  # Data
  rf_finger = generate_finger("rf", 0.0)
  mf_finger = generate_finger("mf", 0.0)
  if_finger = generate_finger("if", 0.0)
  figngers = [rf_finger, mf_finger, if_finger]
  fingers_links = "\n".join(link_urdf(l) for l in fingers.links)
  joints_urdf = "\n".join(joint_urdf(j) for j in fingers.joints)
  
  return fingers_links, joints_urdf

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

def render_hand_joints_urdf() -> str:
  fingers_links, joints_urdf = generate_mf_rf_if()
  palm_link = get_palm_constant()
    return f"""
  <?xml version="1.0" ?>
  <robot name="xela_palm_generated">
  {palm_link}
  {fingers_links}
  {joints_urdf}


  </robot>
  """.rstrip("\n")





if __name__ == "__main__":
    print(palm_joints_urdf())

