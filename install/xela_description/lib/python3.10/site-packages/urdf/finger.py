from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string


JOINT_CONFIG_FILE = "../joint_config.json"

def load_joint_config(file_path: str) -> dict[str, Any]:
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading joint config: {e}")
        return None


class MCPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    # For now this template generates a single link (p4_unified),
    # matching `urdf/robot.urdf`.
    def link_name(self) -> str:
        return f"{self.prefix}_mcp"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0342889, -0.0265621, -0.0145004], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.044,
            "inertia": {
                "ixx": 6.90801e-06,
                "ixy": 2.26365e-06,
                "ixz": 1.79475e-07,
                "iyy": 1.04766e-05,
                "iyz": -1.82708e-07,
                "izz": 1.10431e-05,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0048, -0.0, -0.0145], "rpy": [1.5708, 1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p4_unified.stl"}},
            "material": {
                "name": "p4_unified_material",
                "color": {"rgba": [0.972549, 0.529412, 0.00392157, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0048, -0.0, -0.0145], "rpy": [1.5708, 1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p4_unified.stl"}},
        }


class PIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_pip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [-0.000258994, 0.00848001, 0.0133488], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.032,
            "inertia": {
                "ixx": 3.54425e-06,
                "ixy": -1.6457e-08,
                "ixz": -1.5221e-08,
                "iyy": 2.67248e-06,
                "iyz": -1.71388e-07,
                "izz": 3.5384e-06,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0075, 0.0], "rpy": [-1.5708, -1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p3_unified.stl"}},
            "material": {
                "name": "p3_unified_material",
                "color": {"rgba": [0.972549, 0.529412, 0.00392157, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0075, 0.0], "rpy": [-1.5708, -1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p3_unified.stl"}},
        }


class DIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_dip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0304899, -0.00688132, -0.0146269], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.037,
            "inertia": {
                "ixx": 8.11059e-06,
                "ixy": 5.66349e-07,
                "ixz": 1.88699e-07,
                "iyy": 6.98155e-06,
                "iyz": -9.6344e-08,
                "izz": 9.0141e-06,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.00905, -0.0, -0.0145], "rpy": [1.5708, 1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p2_unified.stl"}},
            "material": {
                "name": "p2_unified_material",
                "color": {"rgba": [0.768627, 0.886275, 0.952941, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.00905, -0.0, -0.0145], "rpy": [1.5708, 1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/p2_unified.stl"}},
        }


class FingertipLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [-0.00193531, -0.0359351, 0.0145854], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.016,
            "inertia": {
                "ixx": 1.0779e-05,
                "ixy": 1.57487e-07,
                "ixz": -2.8587e-08,
                "iyy": 5.55855e-06,
                "iyz": -1.64744e-07,
                "izz": 1.00656e-05,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [-0.00135925, -0.025, 0.0145], "rpy": [-1.5708, -1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/fingertop_unfied.stl"}},
            "material": {
                "name": "fingertop_unfied_material",
                "color": {"rgba": [0.917647, 0.917647, 0.917647, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [-0.00135925, -0.025, 0.0145], "rpy": [-1.5708, -1.5708, 0.0]},
            "geometry": {"mesh": {"filename": "package://assets/fingertop_unfied.stl"}},
        }


class RELATIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_realtip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.000001,
            "inertia": {
                "ixx": 0.000025,
                "ixy": 0.0,
                "ixz": 0.0,
                "iyy": 0.000025,
                "iyz": 0.0,
                "izz": 0.000025,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "geometry": {"sphere": {"radius": 0.005}},
            "material": {
                "name": "ball_material",
                "color": {"rgba": [1.0, 0.0, 0.0, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "geometry": {"sphere": {"radius": 0.005}},
        }

class ROTJOINT:
    def __init__(self, prefix: str, offset: float, joint_config: dict[str, Any]):
        self.prefix = prefix
        self.offset = offset
        self.joint_config = joint_config
    def joint_name(self) -> str:
        return f"{self.prefix}_rot"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.0326 + self.offset, -0.0123, -0.0145], "rpy": [-1.5708, -1.5708, 0.0]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_mcp"

    def child_link_name(self) -> str:
        return f"{self.prefix}_pip"

    def axis(self) -> list[float]:
        return [0.0, 0.0, 1.0]

    def limit(self) -> dict[str, Any]:
        return {"effort": self.joint_config["effort"], "velocity": self.joint_config["velocity"], "lower": self.joint_config["lower"], "upper": self.joint_config["upper"]}


class PIPJOINT:
    def __init__(self, prefix: str, offset: float, joint_config: dict[str, Any]):
        self.prefix = prefix
        self.offset = offset
        self.joint_config = joint_config

    def joint_name(self) -> str:
        return f"{self.prefix}_pip"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.0145 + self.offset, 0.015, 0.013], "rpy": [1.5708, 0.0, 1.5708]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_pip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_dip"

    def axis(self) -> list[float]:
        return [0.0, 0.0, 1.0]

    def limit(self) -> dict[str, Any]:
        return {"effort": self.joint_config["effort"], "velocity": self.joint_config["velocity"], "lower": self.joint_config["lower"], "upper": self.joint_config["upper"]}


class DIPJOINT:
    def __init__(self, prefix: str, offset: float, joint_config: dict[str, Any]):
        self.prefix = prefix
        self.offset = offset
        self.joint_config = joint_config

    def joint_name(self) -> str:
        return f"{self.prefix}_dip"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.0361 + self.offset, 0.0, -0.0291], "rpy": [0.0, 0.0, 1.5708]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_dip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def axis(self) -> list[float]:
        return [0.0, 0.0, 1.0]

    def limit(self) -> dict[str, Any]:
        return {"effort": self.joint_config["effort"], "velocity": self.joint_config["velocity"], "lower": self.joint_config["lower"], "upper": self.joint_config["upper"]}

class RELATIPJOINT:
    def __init__(self, prefix: str, offset: float):
        self.prefix = prefix
        self.offset = offset

    def joint_name(self) -> str:
        return f"{self.prefix}_realtip"

    def joint_type(self) -> str:
        return "fixed"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.02, -0.07, 0.015], "rpy": [0.0, 0.0, 0.0]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_realtip"
    def axis(self) -> list[float]:
        return [0.0, 0.0, -1.0]

    def limit(self) -> dict[str, Any]:
        return None


# Fingertip sparse-skin frame suffix matches leapXela_ss/robot.urdf naming.
_FINGERTIP_SS_SUFFIX = {"rf": "1", "mf": "4", "if": "4"}
_FINGERTIP_SS_XYZ = [-0.0139201, -0.025, 0.0145]
_FINGERTIP_SS_RPY = [3.14159, -1.5708, 0.0]


class SparseSkinFrameLink:
    """Dummy inertial-only link used as a sparse-skin sensor frame."""

    def __init__(self, name: str):
        self._name = name

    def link_name(self) -> str:
        return self._name

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 1e-9,
            "inertia": {
                "ixx": 0.0,
                "ixy": 0.0,
                "ixz": 0.0,
                "iyy": 0.0,
                "iyz": 0.0,
                "izz": 0.0,
            },
        }

    def visual(self) -> None:
        return None

    def collision(self) -> None:
        return None


class SparseSkinFrameJoint:
    """Fixed joint attaching a sparse-skin frame to a finger link."""

    def __init__(
        self,
        joint_name: str,
        parent_link: str,
        child_link: str,
        xyz: list[float],
        rpy: list[float],
    ):
        self._joint_name = joint_name
        self._parent_link = parent_link
        self._child_link = child_link
        self._xyz = xyz
        self._rpy = rpy

    def joint_name(self) -> str:
        return self._joint_name

    def joint_type(self) -> str:
        return "fixed"

    def origin(self) -> dict[str, Any]:
        return {"xyz": self._xyz, "rpy": self._rpy}

    def parent_link_name(self) -> str:
        return self._parent_link

    def child_link_name(self) -> str:
        return self._child_link

    def axis(self) -> list[float]:
        return [0.0, 0.0, 0.0]

    def limit(self) -> None:
        return None


def _sparseskin_frames(prefix: str) -> tuple[list[Any], list[Any]]:
    """Dummy links + fixed joints for finger sparse-skin frames."""
    # Sensor IDs aligned with Allegro/XELA naming (if / mf / rf).
    prefixes_by_finger = {
        "rf": {"A": 9, "C": 10, "Tip": 2},
        "mf": {"A": 5, "C": 6, "Tip": 1},
        "if": {"A": 1, "C": 2, "Tip": 0},
    }
    prefixes = prefixes_by_finger[prefix]
    tip_name = f"{prefixes['Tip']}aftc_palm_link"

    specs = [
        (
            f"link_{prefixes['A']}A_4x4_palm_link",
            f"{prefix}_pip",
            [-0.0113381, 0.0245413, 0.023],
            [0.0, 0.0, -1.5708],
        ),
        (
            f"link_{prefixes['C']}_4x4_palm_link",
            f"{prefix}_dip",
            [0.045226, 0.0095, -0.0259],
            [1.5708, 0.0, 3.14159],
        ),
        (
            tip_name,
            f"{prefix}_fingertip",
            list(_FINGERTIP_SS_XYZ),
            list(_FINGERTIP_SS_RPY),
        ),
    ]

    links: list[Any] = []
    joints: list[Any] = []
    for frame_name, parent, xyz, rpy in specs:
        links.append(SparseSkinFrameLink(frame_name))
        joints.append(
            SparseSkinFrameJoint(
                joint_name=f"{frame_name}_frame",
                parent_link=parent,
                child_link=frame_name,
                xyz=xyz,
                rpy=rpy,
            )
        )
    return links, joints


@dataclass(frozen=True)
class Finger:
    prefix: str
    links: list[Any]
    joints: list[Any]


def generate_finger(
    prefix: str, offset: float, teleop: bool = False, sparseskin: bool = False
) -> Finger:
  
    joint_config = load_joint_config(JOINT_CONFIG_FILE)["leapXela"]["sim"]["fingers"]
    links = [MCPLink(prefix), PIPLink(prefix), DIPLink(prefix), FingertipLink(prefix)]
    joints = [
        ROTJOINT(prefix, offset, joint_config["rot"]),
        PIPJOINT(prefix, offset, joint_config["pip"]),
        DIPJOINT(prefix, offset, joint_config["dip"]),
    ]


    if teleop:
        links += [RELATIPLink(prefix)]
        joints += [RELATIPJOINT(prefix, offset)]

    if sparseskin:
        ss_links, ss_joints = _sparseskin_frames(prefix)
        links += ss_links
        joints += ss_joints

    return Finger(prefix, links, joints)


def link_urdf(link: Any) -> str:
    inertial = link.inertial()
    visual = link.visual()
    collision = link.collision()

    visual_xml = ""
    collision_xml = ""
    if visual is not None:
        if "mesh" in visual["geometry"].keys():
            mesh_visual_xml = f"""<mesh filename="{visual["geometry"]["mesh"]["filename"]}"/>"""
        else:
            mesh_visual_xml = f"""<sphere radius="{visual["geometry"]["sphere"]["radius"]}"/>"""
        visual_xml = f"""
    <visual>
      <origin xyz="{list_to_string(visual["origin"]["xyz"])}" rpy="{list_to_string(visual["origin"]["rpy"])}"/>
      <geometry>
        {mesh_visual_xml}
      </geometry>
      <material name="{visual["material"]["name"]}">
        <color rgba="{list_to_string(visual["material"]["color"]["rgba"])}"/>
      </material>
    </visual>"""
    if collision is not None:
        if "mesh" in collision["geometry"].keys():
            mesh_collision_xml = f"""<mesh filename="{collision["geometry"]["mesh"]["filename"]}"/>"""
        else:
            mesh_collision_xml = f"""<sphere radius="{collision["geometry"]["sphere"]["radius"]}"/>"""
        collision_xml = f"""
    <collision>
      <origin xyz="{list_to_string(collision["origin"]["xyz"])}" rpy="{list_to_string(collision["origin"]["rpy"])}"/>
      <geometry>
        {mesh_collision_xml}
      </geometry>
    </collision>"""

    return f"""
  <link name="{link.link_name()}">
    <inertial>
      <origin xyz="{list_to_string(inertial["origin"]["xyz"])}" rpy="{list_to_string(inertial["origin"]["rpy"])}"/>
      <mass value="{inertial["mass"]}"/>
      <inertia ixx="{inertial["inertia"]["ixx"]}" ixy="{inertial["inertia"]["ixy"]}" ixz="{inertial["inertia"]["ixz"]}" iyy="{inertial["inertia"]["iyy"]}" iyz="{inertial["inertia"]["iyz"]}" izz="{inertial["inertia"]["izz"]}"/>
    </inertial>{visual_xml}{collision_xml}
  </link>
""".rstrip(
        "\n"
    )


def joint_urdf(joint: Any) -> str:
    limit = joint.limit()
    origin = joint.origin()
    
    limit_xml = ""
    if limit is not None:
        limit_xml = f"""<limit effort="{limit["effort"]}" velocity="{limit["velocity"]}" lower="{limit["lower"]}" upper="{limit["upper"]}"/>"""

     
    return f"""
  <joint name="{joint.joint_name()}" type="{joint.joint_type()}">
    <origin xyz="{list_to_string(origin["xyz"])}" rpy="{list_to_string(origin["rpy"])}"/>
    <parent link="{joint.parent_link_name()}"/>
    <child link="{joint.child_link_name()}"/>
    <axis xyz="{list_to_string(joint.axis())}"/>
    {limit_xml}
  </joint>
""".rstrip(
        "\n"
    )


def render_finger_urdf(finger: Finger) -> str:
    links_xml = "\n".join(link_urdf(l) for l in finger.links)
    joints_xml = "\n".join(joint_urdf(j) for j in finger.joints)

    return f"""<?xml version="1.0" ?>
<robot name="xela_finger_generated">
{links_xml}
{joints_xml}

<link name="base"/>
<joint name="base" type="fixed">
  <origin xyz="0 0 0.2" rpy="1.57 0 0"/>
  <parent link="base"/>
  <child link="{finger.links[0].link_name()}"/>
</joint>
</robot>
"""


def write_finger_urdf(file_path: str, finger: Finger) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(render_finger_urdf(finger))


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Generate finger URDF.")
    parser.add_argument("--prefix", default="rf", help="Finger prefix (rf/mf/if)")
    parser.add_argument(
        "--sparseskin",
        action="store_true",
        default=False,
        help="Include sparse-skin sensor frames on the finger",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=None,
        help="Output URDF path (default: OUT env or finger.urdf)",
    )
    args = parser.parse_args()

    finger = generate_finger(args.prefix, 0.0, sparseskin=args.sparseskin)
    out_path = args.out or os.environ.get("OUT") or "finger.urdf"
    write_finger_urdf(out_path, finger)
    print(f"Wrote {out_path}")

