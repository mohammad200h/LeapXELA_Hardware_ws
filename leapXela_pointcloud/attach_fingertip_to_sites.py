import mujoco as mj


SITES = ["rf_pointcloud", "mf_pointcloud", "if_pointcloud", "th_pointcloud"]



def get_fingertip_spec():
    spec = mj.MjSpec.from_file("fingertip.xml")
    return spec

def get_robot_spec():
    spec = mj.MjSpec.from_file("robot.xml")
    return spec

def attach_fingertip_to_sites(fingertip_spec, robot_spec):
    for site_name in SITES:
        site = robot_spec.site(site_name)

        # In MuJoCo's Python model-editing API, a body element cannot be attached
        # into multiple parents. Load a fresh fingertip spec per site so each
        # attachment uses a distinct body subtree.
        local_fingertip_spec = mj.MjSpec.from_file("fingertip.xml")
        root_body = local_fingertip_spec.body("root")
        attached_body = site.attach_body(root_body, prefix=f"{site_name}_", suffix="")

        # `fingertip.xml` has a freejoint on the root body; once attached to a site
        # we want the subtree to be rigidly attached (no extra DoFs).
        for j in list(attached_body.joints):
            if j.type == mj.mjtJoint.mjJNT_FREE:
                robot_spec.delete(j)

    return robot_spec


if __name__ == "__main__":
    fingertip_spec = get_fingertip_spec()
    robot_spec = get_robot_spec()
    attach_fingertip_to_sites(fingertip_spec, robot_spec)

    # Compile once before exporting XML.
    robot_spec.compile()
    with open("robot_with_fingertips.xml", "w", encoding="utf-8") as f:
        f.write(robot_spec.to_xml())