from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string


class MCPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    # Matching `urdf/robot.urdf` link `mcp_joint`.
    def link_name(self) -> str:
        return f"{self.prefix}_mcp"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.044,
            "inertia": {
                "ixx": 0.000011499,
                "ixy": 0.000003049,
                "ixz": 0.000000121,
                "iyy": 0.000007796,
                "iyz": 0.000000112,
                "izz": 0.000014759,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.008406902261174496, 0.007766243859716995 , 0.014657354985032912],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/mcp_joint.stl"}},
            "material": {
                "name": "mcp_joint_material",
                "color": {"rgba": [0.866667, 0.866667, 0.0509804, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.008406902261174496, 0.007766243859716995, 0.014657354985032912],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/mcp_joint.stl"}},
        }


class PIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_pip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.032,
            "inertia": {
                "ixx": 0.000004798,
                "ixy": 0.000000012,
                "ixz": 0.000000004,
                "iyy": 0.000002862,
                "iyz": 0.000000011,
                "izz": 0.000004234,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.009643363092271328, 0.0003, 0.0007840340104173765],
                "rpy": [-1.5708, -1.5708, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/pip.stl"}},
            "material": {
                "name": "pip_material",
                "color": {"rgba": [0.74902, 0.74902, 0.74902, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.009643363092271328, 0.0003, 0.0007840340104173765],
                "rpy": [-1.5708, -1.5708, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/pip.stl"}},
        }


class DIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_dip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.037,
            "inertia": {
                "ixx": 0.000005542,
                "ixy": -0.000000607,
                "ixz": -0.000000017,
                "iyy": 0.000005727,
                "iyz": -0.000000023,
                "izz": 0.000006682,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.021133352895225003, -0.00843211914670488, 0.00978508816209524],
                "rpy": [-3.1416, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/dip.stl"}},
            "material": {
                "name": "dip_material",
                "color": {"rgba": [0.866667, 0.866667, 0.0509804, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.021133352895225003, -0.00843211914670488, 0.00978508816209524],
                "rpy": [-3.1416, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/dip.stl"}},
        }


class FingertipLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.016,
            "inertia": {
                "ixx": 0.000003368,
                "ixy": 0.000000115,
                "ixz": 0.0,
                "iyy": 0.000001556,
                "iyz": 0.0,
                "izz": 0.000002863,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.013286424108533503, -0.006114238386541987, 0.0145],
                "rpy": [3.1416, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/fingertip.stl"}},
            "material": {
                "name": "fingertip_material",
                "color": {"rgba": [0.866667, 0.866667, 0.0509804, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.013286424108533503, -0.006114238386541987, 0.0145],
                "rpy": [3.1416, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/fingertip.stl"}},
        }


class RELATIPLink:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def link_name(self) -> str:
        return f"{self.prefix}_realtip"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.1,
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
    def __init__(self, prefix: str, offset: float):
        self.prefix = prefix
        self.offset = offset

    def joint_name(self) -> str:
        return f"{self.prefix}_rot"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-0.012200000000000007713, 0.038099999999999994982 + self.offset, 0.014500000000000000736], 
        "rpy": [-1.570796326794896558, 0.0, 1.5707963267948943376]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_mcp"

    def child_link_name(self) -> str:
        return f"{self.prefix}_pip"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -1.047, "upper":1.047}


class PIPJOINT:
    def __init__(self, prefix: str, offset: float):
        self.prefix = prefix
        self.offset = offset

    def joint_name(self) -> str:
        return f"{self.prefix}_pip"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.01499999999999996822, 0.014299999999999904801 + self.offset, -0.012999999999999824196], 
        "rpy": [1.571, -1.571, 0]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_pip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_dip"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.506, "upper": 1.885}


class DIPJOINT:
    def __init__(self, prefix: str, offset: float):
        self.prefix = prefix
        self.offset = offset

    def joint_name(self) -> str:
        return f"{self.prefix}_dip"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-4.0880582495572692636e-09, -0.036100004210367367397 + self.offset, 0.00020000000000007858714], 
        "rpy": [0.0, 0.0, 0.0]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_dip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.366, "upper": 2.042}

class RELATIPJOINT:
    def __init__(self, prefix: str, offset: float):
        self.prefix = prefix
        self.offset = offset

    def joint_name(self) -> str:
        return f"{self.prefix}_realtip"

    def joint_type(self) -> str:
        return "fixed"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.02 , -0.07 + self.offset, 0.015], "rpy": [0.0, 0.0, 0.0]}

    def parent_link_name(self) -> str:
        return f"{self.prefix}_fingertip"

    def child_link_name(self) -> str:
        return f"{self.prefix}_realtip"
    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return None
        
    
@dataclass(frozen=True)
class Finger:
    prefix: str
    links: list[Any]
    joints: list[Any]


def generate_finger(prefix: str, offset: float, teleop = True) -> Finger:
    mcp = MCPLink(prefix)
    pip = PIPLink(prefix)
    dip = DIPLink(prefix)
    fingertip = FingertipLink(prefix)
    realtip = RELATIPLink(prefix)

    links = [mcp, pip, dip, fingertip]
    joints = [ ROTJOINT(prefix, offset), PIPJOINT(prefix, offset), DIPJOINT(prefix, offset)]

    if teleop:
        links += [realtip]
        joints += [RELATIPJOINT(prefix, offset)]

    return Finger(prefix, links, joints)


def link_urdf(link: Any) -> str:
    inertial = link.inertial()
    visual = link.visual()
    collision = link.collision()
    
    if "mesh" in visual["geometry"].keys():
        mesh_visual_xml = f"""<mesh filename="{visual["geometry"]["mesh"]["filename"]}"/>"""
    else:
        mesh_visual_xml = f"""<sphere radius="{visual["geometry"]["sphere"]["radius"]}"/>"""
    if "mesh" in collision["geometry"].keys():
        mesh_collision_xml = f"""<mesh filename="{collision["geometry"]["mesh"]["filename"]}"/>"""
    else:
        mesh_collision_xml = f"""<sphere radius="{collision["geometry"]["sphere"]["radius"]}"/>"""

    return f"""
  <link name="{link.link_name()}">
    <inertial>
      <origin xyz="{list_to_string(inertial["origin"]["xyz"])}" rpy="{list_to_string(inertial["origin"]["rpy"])}"/>
      <mass value="{inertial["mass"]}"/>
      <inertia ixx="{inertial["inertia"]["ixx"]}" ixy="{inertial["inertia"]["ixy"]}" ixz="{inertial["inertia"]["ixz"]}" iyy="{inertial["inertia"]["iyy"]}" iyz="{inertial["inertia"]["iyz"]}" izz="{inertial["inertia"]["izz"]}"/>
    </inertial>
    <visual>
      <origin xyz="{list_to_string(visual["origin"]["xyz"])}" rpy="{list_to_string(visual["origin"]["rpy"])}"/>
      <geometry>
        {mesh_visual_xml}
      </geometry>
      <material name="{visual["material"]["name"]}">
        <color rgba="{list_to_string(visual["material"]["color"]["rgba"])}"/>
      </material>
    </visual>
    <collision>
      <origin xyz="{list_to_string(collision["origin"]["xyz"])}" rpy="{list_to_string(collision["origin"]["rpy"])}"/>
      <geometry>
        {mesh_collision_xml}
      </geometry>
    </collision>
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
    import os

    finger = generate_finger("rf", 0.0)
    out_path = os.environ.get("OUT") or "finger.urdf"
    write_finger_urdf(out_path, finger)
    print(f"Wrote {out_path}")

