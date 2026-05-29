from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class CMCLink:
    def link_name(self) -> str:
        return "cmc"

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
                "xyz": [-0.005356636907728671, 0.0003, 0.0007840340104173782],
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
                "xyz": [-0.005356636907728671, 0.0003, 0.0007840340104173782],
                "rpy": [-1.5708, -1.5708, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/pip.stl"}},
        }


class AXLLink:
    def link_name(self) -> str:
        return "axl"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.003,
            "inertia": {
                "ixx": 0.000000593,
                "ixy": 0.0,
                "ixz": 0.0,
                "iyy": 0.000000549,
                "iyz": 0.0,
                "izz": 0.000000224,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.011961920770611187, 0.0, -0.0158526489566642],
                "rpy": [1.5708, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_pip.stl"}},
            "material": {
                "name": "thumb_pip_material",
                "color": {"rgba": [0.866667, 0.866667, 0.0509804, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.011961920770611187, 0.0, -0.0158526489566642],
                "rpy": [1.5708, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_pip.stl"}},
        }


class MCPLink:
    def link_name(self) -> str:
        return "th_mcp"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.038,
            "inertia": {
                "ixx": 0.000008474,
                "ixy": 0.000000241,
                "ixz": 0.000000026,
                "iyy": 0.000003841,
                "iyz": 0.000000025,
                "izz": 0.000007679,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.043968715707239175, 0.0579529529737092, -0.008628676449369476],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_dip.stl"}},
            "material": {
                "name": "thumb_dip_material",
                "color": {"rgba": [0.866667, 0.866667, 0.0509804, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.043968715707239175, 0.0579529529737092, -0.008628676449369476],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_dip.stl"}},
        }


class IPLLink:
    def link_name(self) -> str:
        return "th_ipl"

    def inertial(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "mass": 0.049,
            "inertia": {
                "ixx": 0.000020372,
                "ixy": -0.000000489,
                "ixz": -0.00000003,
                "iyy": 0.000004336,
                "iyz": -0.000000097,
                "izz": 0.000019845,
            },
        }

    def visual(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.06255953846266739, 0.07845968291139699, 0.048992911807332215],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_fingertip.stl"}},
            "material": {
                "name": "thumb_fingertip_material",
                "color": {"rgba": [0.603922, 0.14902, 0.14902, 1.0]},
            },
        }

    def collision(self) -> dict[str, Any]:
        return {
            "origin": {
                "xyz": [0.06255953846266739, 0.07845968291139699, 0.048992911807332215],
                "rpy": [0.0, 0.0, 0.0],
            },
            "geometry": {"mesh": {"filename": "package://assets/thumb_fingertip.stl"}},
        }


class THREALTIPLINK:
    def link_name(self) -> str:
        return "th_realtip"
    
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
                "name": "th_realtip_material",
                "color": {"rgba": [0.0, 0.0, 1.0, 1.0]},
            },
        }
    def collision(self) -> dict[str, Any]:
        return {
            "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
            "geometry": {"sphere": {"radius": 0.005}},
        }
    
class THAXLJOINT:
    def joint_name(self) -> str:
        return "th_axl"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-2.7755575615628913511e-17, 0.014300000000000005415, -0.013000000000000011546], 
        "rpy": [1.5707963267948958919, -1.570796326794896336, 0]}

    def parent_link_name(self) -> str:
        return "cmc"

    def child_link_name(self) -> str:
        return "axl"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -0.47, "upper": 2.443}


class THMCPJOINT:
    def joint_name(self) -> str:
        return "th_mcp"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [0, 0.014499999999999966041, -0.017000000000000053263], 
        "rpy": [-1.570796326794896558, 1.6050198443300131245e-46, -1.9721522630516624601e-31]}

    def parent_link_name(self) -> str:
        return "axl"

    def child_link_name(self) -> str:
        return "th_mcp"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -1.20, "upper": 1.90}


class THIPLJOINT:
    def joint_name(self) -> str:
        return "th_ipl"

    def joint_type(self) -> str:
        return "revolute"

    def origin(self) -> dict[str, Any]:
        return {"xyz": [-1.249000902703301108e-16, 0.046599999999999863753, 0.00019999999999997710581], 
        "rpy": [1.5063958491491781023e-44, 5.4234187233935260503e-31, 3.141592653589793116]}

    def parent_link_name(self) -> str:
        return "th_mcp"

    def child_link_name(self) -> str:
        return "th_ipl"

    def axis(self) -> list[float]:
        return [0, 0, -1]

    def limit(self) -> dict[str, Any]:
        return {"effort": 0.95, "velocity": 8.48, "lower": -1.34, "upper": 1.88}

class THREALTIPJOINT:
    def joint_name(self) -> str:
        return "th_realtip"
    
    def joint_type(self) -> str:
        return "fixed"
    
    def origin(self) -> dict[str, Any]:
        return {"xyz": [0.00, -0.07, -0.015], 
        "rpy": [4.5935029425113685044e-17, -2.8730071914463794583e-16, 4.4395481053923607589e-32]}
    def parent_link_name(self) -> str:
        return "th_ipl"
    def child_link_name(self) -> str:
        return "th_realtip"
    def axis(self) -> list[float]:
        return [0, 0, -1]
    def limit(self) -> dict[str, Any]:
        return None

@dataclass(frozen=True)
class Thumb:
    links: list[Any]
    joints: list[Any]


def generate_thumb(teleop: bool = True) -> Thumb:
    links = [CMCLink(), AXLLink(), MCPLink(), IPLLink()]
    joints = [ THAXLJOINT(), THMCPJOINT(), THIPLJOINT()]

    if teleop:
        links +=[THREALTIPLINK()]
        joints +=[THREALTIPJOINT()]
    return Thumb(links=links, joints=joints)


def link_urdf(link: Any) -> str:
    inertial = link.inertial()
    visuals = _as_list(link.visual())
    collisions = _as_list(link.collision())

    visuals_xml = ""
    collisions_xml = ""
    for v in visuals:
        if "mesh" in v["geometry"].keys():
            mesh_visual_xml = f"""<mesh filename="{v["geometry"]["mesh"]["filename"]}"/>"""
        else:
            mesh_visual_xml = f"""<sphere radius="{v["geometry"]["sphere"]["radius"]}"/>"""

        visuals_xml += f"""\n
    <visual>
      <origin xyz="{list_to_string(v["origin"]["xyz"])}" rpy="{list_to_string(v["origin"]["rpy"])}"/>
      <geometry>
        {mesh_visual_xml}
      </geometry>
      <material name="{v["material"]["name"]}">
        <color rgba="{list_to_string(v["material"]["color"]["rgba"])}"/>
      </material>
    </visual>
    """
    for c in collisions:
        if "mesh" in c["geometry"].keys():
            mesh_collision_xml = f"""<mesh filename="{c["geometry"]["mesh"]["filename"]}"/>"""
        else:
            mesh_collision_xml = f"""<sphere radius="{c["geometry"]["sphere"]["radius"]}"/>"""
        collisions_xml += f"""\n
    <collision>
      <origin xyz="{list_to_string(c["origin"]["xyz"])}" rpy="{list_to_string(c["origin"]["rpy"])}"/>
      <geometry>
        {mesh_collision_xml}
      </geometry>
    </collision>
    """

    return f"""
  <link name="{link.link_name()}">
    <inertial>
      <origin xyz="{list_to_string(inertial["origin"]["xyz"])}" rpy="{list_to_string(inertial["origin"]["rpy"])}"/>
      <mass value="{inertial["mass"]}"/>
      <inertia ixx="{inertial["inertia"]["ixx"]}" ixy="{inertial["inertia"]["ixy"]}" ixz="{inertial["inertia"]["ixz"]}" iyy="{inertial["inertia"]["iyy"]}" iyz="{inertial["inertia"]["iyz"]}" izz="{inertial["inertia"]["izz"]}"/>
    </inertial>
{visuals_xml}
{collisions_xml}
  </link>
""".rstrip("\n")


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
""".rstrip("\n")


def render_thumb_urdf(thumb: Thumb) -> str:
    links_xml = "\n".join(link_urdf(l) for l in thumb.links)
    joints_xml = "\n".join(joint_urdf(j) for j in thumb.joints)

    return f"""<?xml version="1.0" ?>
<robot name="xela_thumb_generated">
{links_xml}
{joints_xml}
<link name="base"/>
<joint name="base" type="fixed">
  <origin xyz="0 0 0.2" rpy="1.57 0 0"/>
  <parent link="base"/>
  <child link="{thumb.links[0].link_name()}"/>
</joint>
</robot>
"""


def write_thumb_urdf(file_path: str, thumb: Thumb) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(render_thumb_urdf(thumb))


if __name__ == "__main__":
    import os

    thumb = generate_thumb()
    out_path = os.environ.get("OUT") or "thumb.urdf"
    write_thumb_urdf(out_path, thumb)
    print(f"Wrote {out_path}")
