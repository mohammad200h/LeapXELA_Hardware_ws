
import mujoco as mj
import pprint
import json

# [x_min, x_max, y_min, y_max, z_min, z_max]
SLIDER_JOINT_LIMITS = [(-0.0015, 0.0015), (-0.0015, 0.0015), (-0.001, 0)]
_4_4_OFFSET = [4.70/1000, 4.25/1000]
_4_6_OFFSET = [7.25/1000, 7.25/1000]
_4_4_Z_POS = 0.005
_4_6_Z_POS = _4_4_Z_POS
SPHERE_SIZE = [0.002]*3


def load_fingertip_magnet_pose():
    with open("fingertip_magnet_pose.json", "r") as f:
        return json.load(f)
    return None

def load_4_4_sites():
    with open("4_4_sites.json", "r") as f:
        return json.load(f)

def load_4_6_sites():
    with open("4_6_sites.json", "r") as f:
        return json.load(f)

def remove_contact_detection_between_grid_elements_of_sensor(spec,geoms_name):
    for geom_name in geoms_name:
        for other_geom_name in geoms_name:
            if geom_name != other_geom_name:
                spec.add_exclude(bodyname1 = geom_name, bodyname2 = other_geom_name)

def make_visual_geoms_of_the_hand_transparent(spec):
    m = spec.material("black")
    rgba = m.rgba
    rgba[3] = 0.2
    print(spec.material("black").rgba)

def remove_collsions_geom_convering_sensors_except_for_finger(spec):
    for idx in range(3):
        name = f"uspa46_{idx+1}"
        geom = spec.geom(name)
        spec.delete(geom)
    
    for finger in ["if", "mf", "rf"]:
        name = f"{finger}_bs_uspa44"
        geom = spec.geom(name)
        spec.delete(geom)
        name = f"{finger}_px_uspa44"
        geom = spec.geom(name)
        spec.delete(geom)
        name = f"{finger}_md_uspa44"
        geom = spec.geom(name)
        spec.delete(geom)
    
    # thumb
    name = "th_px_uspa44"
    geom = spec.geom(name)
    spec.delete(geom)
    name = "th_ds_uspa44"
    geom = spec.geom(name)
    spec.delete(geom)

    ####thumb fingertips####
    name = "th_ds_tip"
    geom = spec.geom(name)
    spec.delete(geom)
    for idx in range(2,7):
        name = f"th_ds_tip_{idx}"
        geom = spec.geom(name)
        spec.delete(geom)
    ####fingers fingertips####
    for finger in ["if", "mf", "rf"]:
        name = f"{finger}_ds_tip"
        geom = spec.geom(name)
        spec.delete(geom)
        for idx in range(2,7):
            name = f"{finger}_ds_tip_{idx}"
            geom = spec.geom(name)
            spec.delete(geom)

def remove_collision_geoms_of_the_hand(spec):
    for geom in spec.geoms:
        if "collision" in geom.name:
            spec.delete(geom)

def add_sensor_patch_to_fingertip(spec,fingertip_magnet_pose, finger_name, sensor_default = None):
    contacts_bodies = []
    joints = {}
    link_name = f"{finger_name}_ds"
    joints[link_name] = {}

    print("finger_name: ", finger_name)
   
    site_pos,sit_quat = fingertip_magnet_pose[f"{finger_name}_pointcloud_base_frame"]["pos"],fingertip_magnet_pose[f"{finger_name}_pointcloud_base_frame"]["quat"]
    parent = spec.body(f"{finger_name}_ds").add_body(
            name=f"{finger_name}_pointcloud_base_frame",
            pos=site_pos,
            quat=sit_quat
            )
    
    for idx in range(0,30):
        joints[link_name][str(idx+1)] = {}
        pos,quat = fingertip_magnet_pose[str(idx+1)]["pos"],fingertip_magnet_pose[str(idx+1)]["quat"]
        name = f"{finger_name}_sensor_{idx+1}"
        
        
        child = parent.add_body(name=name,pos=pos,quat=quat)
       

        # child = spec.body(f"{finger_name}_ds").add_body(name=name,pos=pos,
        #     quat=quat)
        child.add_geom(
            name=f"{finger_name}_sensor_{idx+1}",
            size=SPHERE_SIZE,
            pos=[0,0,0],
            type=mj.mjtGeom.mjGEOM_SPHERE,
            default=sensor_default
        )
        axis_name = "not_set"
        for axis in [[1,0,0],[0,1,0],[0,0,1]]:
            if axis[0] == 1:
                limit = fingertip_magnet_pose[str(idx+1)]["j_x_range"]
                axis_name = "x"
            elif axis[1] == 1:
                limit = fingertip_magnet_pose[str(idx+1)]["j_y_range"]
                axis_name = "y"
            elif axis[2] == 1:
                limit = fingertip_magnet_pose[str(idx+1)]["j_z_range"]
                axis_name = "z"
            else:
                raise ValueError(f"Invalid axis: {axis}")
            joint = child.add_joint(type=mj.mjtJoint.mjJNT_SLIDE,name=name+f"_slide_{axis_name}",axis=axis,range=limit)
            joints[link_name][str(idx+1)][axis_name] = joint.name
        
        contacts_bodies.append(child.name)
    # remove contact detection between grid elements of sensor
    remove_contact_detection_between_grid_elements_of_sensor(spec,contacts_bodies)
    return joints

def _add_uspa44(spec, site_name,link_name,sensor_default):
    contacts_bodies = []
    joints = {}
    joints[site_name] = {}

    site_x0_y0 = spec.site(site_name)
    sites_parent_body = site_x0_y0.parent
    x,y,z = site_x0_y0.pos
    if link_name == "bs":
        y += 0.0025
        euler=[1.57,0,0]    
    elif link_name == "px":
        z -= 0.0025
        euler=[0,0,0] 
    elif link_name == "md":
        y -= 0.0025
        euler=[-1.57,0,-1.57] 
    elif link_name == "th_px":
        y -= 0.0025
        euler=[0,-1.57,0] 
    elif link_name == "th_ds":
        x += 0.0025
        euler=[0,1.57,2*1.57] 

    
    offset = 0.0025*2
    for j in range(4):
        for i in range(4):
            loc = str(i)+"_"+str(j)
            joints[site_name][loc] = {}
            pos = None
            if link_name in ["bs", "md"]:
                pos = [x - offset * i, y, z - offset * j]
            elif link_name =="px":
                pos = [x - offset * j , y - offset * i, z ]
            elif link_name == "th_px":
                pos = [x  , y - offset * i, z - offset * j]       
            elif link_name == "th_ds":
                pos = [x  , y + offset * i, z - offset * j]

            name = f"{site_name}_sensor_patch_{i}_{j}"
            child = sites_parent_body.add_body(name=name,pos=pos,euler=euler)
            child.add_geom(
                name=f"{site_name}_sensor_patch_{i}_{j}",
                type=mj.mjtGeom.mjGEOM_SPHERE,
                size=[0.0025, 0.0025, 0.0025],
                pos=[0,0,0],
                default=sensor_default
            )
            axis_name = "not_set"
            for axis in [[1,0,0],[0,1,0],[0,0,1]]:
                if axis[0] == 1:
                    limit = SLIDER_JOINT_LIMITS[0]
                    axis_name = "x"
                elif axis[1] == 1:
                    limit = SLIDER_JOINT_LIMITS[1]
                    axis_name = "y"
                elif axis[2] == 1:
                    limit = SLIDER_JOINT_LIMITS[2]
                    axis_name = "z"
                else:
                    raise ValueError(f"Invalid axis: {axis}")
                joint = child.add_joint(type=mj.mjtJoint.mjJNT_SLIDE,name=name+f"_slide_{axis_name}",axis=axis,range=limit)
                joints[site_name][loc][axis_name] = joint.name
            contacts_bodies.append(child.name)
    # remove contact detection between grid elements of sensor
    remove_contact_detection_between_grid_elements_of_sensor(spec,contacts_bodies)

    return joints

def lay_down_grid_for_4_4(parent_body,sensor_default):
    contacts_bodies = []
    joints = {}
    sensor_name = parent_body.name
    joints[sensor_name] = {}
    pos = [0,0,_4_4_Z_POS]
    parent_name = parent_body.name
    joints = {}
    joints[parent_name] = {}
    for j in range(4):
        pos[1] += _4_4_OFFSET[0]
        euler = [2*1.57,0,2*1.57]
        for i in range(4):
            name = f"{parent_name}_4_4_sensor_patch_{i}_{j}"
            loc = f"{i}_{j}"
            joints[parent_name][loc] = {}
            pos[0] += _4_4_OFFSET[1]
            child =parent_body.add_body(name=name,pos=pos,euler=euler)
            child.add_geom(
                name=name,
                type=mj.mjtGeom.mjGEOM_SPHERE,
                size=SPHERE_SIZE,
                pos=[0,0,0],
                default=sensor_default
            )
            axis_name = "not_set"
            for axis in [[1,0,0],[0,1,0],[0,0,1]]:
                if axis[0] == 1:
                    limit = SLIDER_JOINT_LIMITS[0]
                    axis_name = "x"
                elif axis[1] == 1:
                    limit = SLIDER_JOINT_LIMITS[1]
                    axis_name = "y"
                elif axis[2] == 1:
                    limit = SLIDER_JOINT_LIMITS[2]
                    axis_name = "z"
                else:
                    raise ValueError(f"Invalid axis: {axis}")
                joint_name = name + f"_slide_{axis_name}"
                print(f"j_name: {joint_name}")
                joint = child.add_joint(
                    type=mj.mjtJoint.mjJNT_SLIDE,
                    name=joint_name,
                    axis=axis,
                    range=limit,
                )
                joints[parent_name][loc][axis_name] = joint.name
            contacts_bodies.append(child.name)
            if i ==3:
                 pos[0] = 0
    
    return contacts_bodies,joints
        
def add_uspa44(spec,_44_sites,sensor_default):
    all_joints = []
    for base_frames,data in _44_sites.items():
        pos = data["pos"]
        quat = data["quat"]
        parent = data["parent"]
        # base frame
        parent = spec.body(parent).add_body(name=base_frames,pos=pos,quat=quat)
        g = parent.add_geom(
            name=base_frames,
            type=mj.mjtGeom.mjGEOM_SPHERE,
            size=[0.0025, 0.0025, 0.0025],
            pos=[0,0,0],
            default=sensor_default
        )
        g.rgba = [1, 1, 0, 1]
    
        contacts_bodies,joints = lay_down_grid_for_4_4(parent,sensor_default)
        remove_contact_detection_between_grid_elements_of_sensor(spec,contacts_bodies)
        all_joints.append(joints)
    return all_joints

def  lay_down_grid_for_4_6(parent_body,sensor_default):
    contacts_bodies = []
    joints = {}
    sensor_name = parent_body.name
    joints[sensor_name] = {}

    pos = [4.55/1000,4.43/1000,_4_6_Z_POS]
    parent_name = parent_body.name
    for j in range(4):
        euler = [2*1.57,0,2*1.57]
        for i in range(6):
            name = f"{parent_name}_4_6_sensor_patch_{i}_{j}"
            print(f"name: {name}")
            loc = f"{i}_{j}"
            joints[sensor_name][loc] = {}
           
            child =parent_body.add_body(name=name,pos=pos,euler=euler)
            child.add_geom(
                name=name,
                type=mj.mjtGeom.mjGEOM_SPHERE,
                size=SPHERE_SIZE,
                pos=[0,0,0],
                default=sensor_default
            )
            pos[0] += _4_6_OFFSET[0]

            axis_name = "not_set"
            for axis in [[1,0,0],[0,1,0],[0,0,1]]:
                if axis[0] == 1:
                    limit = SLIDER_JOINT_LIMITS[0]
                    axis_name = "x"
                elif axis[1] == 1:
                    limit = SLIDER_JOINT_LIMITS[1]
                    axis_name = "y"
                elif axis[2] == 1:
                    limit = SLIDER_JOINT_LIMITS[2]
                    axis_name = "z"
                else:
                    raise ValueError(f"Invalid axis: {axis}")
                joint_name = name + f"_slide_{axis_name}"
                print(f"j_name: {joint_name}")
                joint = child.add_joint(
                    type=mj.mjtJoint.mjJNT_SLIDE,
                    name=joint_name,
                    axis=axis,
                    range=limit,
                )
                joints[sensor_name][loc][axis_name] = joint.name
            contacts_bodies.append(child.name)
            

            if i ==5:
                 pos[0] = 4.55/1000
        pos[1] += _4_6_OFFSET[1]
    
    return contacts_bodies,joints
        

def add_uspa46(spec,_46_sites,sensor_default):
    all_joints = []
    for base_frames,data in _46_sites.items():
        pos = data["pos"]
        quat = data["quat"]
        parent = data["parent"]
        # base frame
        parent = spec.body(parent).add_body(name=base_frames,pos=pos,quat=quat)
        g = parent.add_geom(
            name=base_frames,
            type=mj.mjtGeom.mjGEOM_SPHERE,
            size=[0.0025, 0.0025, 0.0025],
            pos=[0,0,0],
            default=sensor_default
        )
        g.rgba = [1, 1, 0, 1]
        contacts_bodies,joints = lay_down_grid_for_4_6(parent,sensor_default)
        remove_contact_detection_between_grid_elements_of_sensor(spec,contacts_bodies)
        all_joints.append(joints)
   

def _add_uspa46(spec, site_name,sensor_default):
    link_name = site_name
    contacts_bodies = []
    joints = {}
    joints[link_name] = {}

    site_x0_y0 = spec.site(site_name)
    sites_parent_body = site_x0_y0.parent
    x,y,z = site_x0_y0.pos

    x_offset = 0.004*2
    z_offset = 0.0035*2
    y += 0.0025

    size=[0.0025, 0.0025, 0.0035]
    contacts_bodies = []
    for j in range(4):
        for i in range(6):
            loc = str(i)+"_"+str(j)
            joints[link_name][loc] = {}
            name = f"{site_name}_sensor_patch_{i}_{j}"
            child = sites_parent_body.add_body(name=name,pos=[x - x_offset * i, y , z - z_offset * j],euler=[1.57,0,0])
            child.add_geom(
                name=f"{site_name}_sensor_patch_{i}_{j}",
                type=mj.mjtGeom.mjGEOM_SPHERE,
                size = size,
                pos=[0,0,0],
                default=sensor_default
            )
            axis_name = "not_set"
            for axis in [[1,0,0],[0,1,0],[0,0,1]]:
                if axis[0] == 1:
                    limit = SLIDER_JOINT_LIMITS[0]
                    axis_name = "x"
                elif axis[1] == 1:
                    limit = SLIDER_JOINT_LIMITS[1]
                    axis_name = "y"
                elif axis[2] == 1:
                    limit = SLIDER_JOINT_LIMITS[2]
                    axis_name = "z"
                else:
                    raise ValueError(f"Invalid axis: {axis}")
                joint = child.add_joint(type=mj.mjtJoint.mjJNT_SLIDE,name=name+f"_slide_{axis_name}",axis=axis,range=limit)
                joints[link_name][loc][axis_name] = joint.name
            contacts_bodies.append(child.name)
    # remove contact detection between grid elements of sensor
    remove_contact_detection_between_grid_elements_of_sensor(spec,contacts_bodies)

    return joints

def write_xml_model(spec):
  xml = spec.to_xml()
  
  with open("leapXela_touch_point_cloud.xml", "w") as f:
    f.write(xml)

def write_scene_xml(spec):
    template = f"""
    <mujoco model="scene_touch_point_cloud">
        <include file="leapXela_touch_point_cloud.xml"/>
        <statistic extent=".6" />
        <visual>
            <headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0" />
            <rgba haze="0.15 0.25 0.35 1" />
            <global azimuth="180" elevation="-50"/>
        </visual>

        <asset>
            <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512"
                height="3072" />
            <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4"
                rgb2="0.1 0.2 0.3"
                markrgb="0.8 0.8 0.8" width="300" height="300" />
            <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5"
                reflectance="0.2" />
        </asset>

        <worldbody>
            <light pos="0 0 3.5" dir="0 0 -1" directional="true" />
            <geom name="floor" size="0 0 0.05" pos="0 0 0" type="plane" material="groundplane" />
        </worldbody>

    </mujoco>
    """
    with open("scene_touch_point_cloud.xml", "w") as f:
        f.write(template)

def wrtie_sensor_joints_to_json(joints):
    with open("sensor_joints.json", "w") as f:
        json.dump(joints, f)

if __name__ == "__main__":
    spec = mj.MjSpec.from_file("leapXela_base_model.xml")
    fingertip_magnet_pose = load_fingertip_magnet_pose()
    _44_sites = load_4_4_sites()
    _46_sites = load_4_6_sites()

    site_names = ["if_bs_uspa44", "mf_bs_uspa44" ,"rf_bs_uspa44",
                  "if_md_uspa44", "mf_md_uspa44" ,"rf_md_uspa44",
                  "if_px_uspa44", "mf_px_uspa44" ,"rf_px_uspa44",
                  
     ]
    th_site_names = ["th_px_uspa44","th_ds_uspa44"]
    palm_site_names = ["uspa46_1", "uspa46_2" ,"uspa46_3"]

    collision_default = spec.geom("if_ds_collision_1").classname
    

    # add sensor_patch to collision default
    sensor_patch_default = spec.add_default("sensor_patch",collision_default)
    sensor_patch_default.geom.size=[0.005, 0.005, 0.005]
    sensor_patch_default.geom.rgba=[1, 0, 0, 1]
    sensor_patch_default.geom.group=2

    make_visual_geoms_of_the_hand_transparent(spec)

    remove_collsions_geom_convering_sensors_except_for_finger(spec)
    remove_collision_geoms_of_the_hand(spec)

    joints = {}
    add_uspa44(spec,_44_sites,sensor_patch_default)

    
    for finger in ["if", "mf", "rf","th"]:
        joints[f"{finger}_ds"] = add_sensor_patch_to_fingertip(spec,fingertip_magnet_pose,finger,sensor_patch_default)[f"{finger}_ds"]
    
    add_uspa46(spec,_46_sites,sensor_patch_default)
    # add sensor_patch to palm
    # for site_name in palm_site_names:
    #     joints[site_name] = add_uspa46(spec, site_name,sensor_patch_default)[site_name]
    # print(joints.keys())
    # pprint.pprint(joints["if_bs_uspa44"])
    wrtie_sensor_joints_to_json(joints)
    write_xml_model(spec)
    write_scene_xml(spec)