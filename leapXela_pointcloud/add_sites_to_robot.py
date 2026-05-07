import mujoco as mj

map = {
    "finger":"rf",
    "finger_2":"mf",
    "finger_3":"if",
    "thumb":"th",

}

def add_sites(spec,map):
    delete_list = []
    for b_name,finger_name in map.items():
        body = spec.body(b_name)
        for geom in body.geoms:
            # add site
            if geom.material == "pointcloud_material" and geom.classname.name == "collision":
                body.add_site(
                    name=f"{finger_name}_pointcloud_base_frame",
                    pos=geom.pos,
                    quat=geom.quat
                )
            # add collision and visual geom to delete list
            if geom.material == "pointcloud_material":
                delete_list.append(geom)

    for geom in delete_list:
        spec.delete(geom)

def write_xml(spec):
    
    with open("robot_with_sites.xml", "w") as f:
        f.write(spec.to_xml())

if __name__ == "__main__":
    spec = mj.MjSpec.from_file("robot.xml")
    add_sites(spec,map)
    write_xml(spec)