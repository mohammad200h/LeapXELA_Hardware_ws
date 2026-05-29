try:
    # When imported as part of the `xela_description` Python package.
    from .list_to_string import list_to_string  # noqa: F401
except ImportError:  # pragma: no cover
    # When executed directly as a script.
    from list_to_string import list_to_string  # noqa: F401


def get_palm_constant() -> str:
    return """
      <link name="palm_lower">
        <visual>
            <origin xyz="-0.020095249652862544332 0.025757756134899473244 -0.034722403578460216134" rpy="0 -0 0" />
            <geometry>
                <mesh filename="assets/palm_lower.stl"/>
            </geometry>
            <material name="palm_lower_material">
                <color rgba="0.60392156862745094426 0.14901960784313725283 0.14901960784313725283 1.0"/>
            </material>
        </visual>
        <collision>
            <origin xyz="-0.020095249652862544332 0.025757756134899473244 -0.034722403578460216134" rpy="0 -0 0" />
            <geometry>
                <mesh filename="assets/palm_lower.stl"/>
            </geometry>
        </collision>
        <inertial>
            <origin xyz="0 0 0" rpy="0 0 0"/>
            <mass value="0.237" />
            <inertia ixx="0.000354094" ixy="-0.000001193" ixz="-0.000002445" iyy="0.000260915" iyz="-0.000002905" izz="0.000529257" />
        </inertial>
    </link>
    """

def render_palm_joints_urdf() -> str:
    palm_link = get_palm_constant()
    return f"""
  <?xml version="1.0" ?>
  <robot name="xela_palm_generated">
  {palm_link}
  </robot>
  """.rstrip("\n")


def write_palm_urdf(file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(render_palm_joints_urdf())


if __name__ == "__main__":
    import os

    out_path = os.environ.get("OUT") or "palm.urdf"
    write_palm_urdf(out_path)

