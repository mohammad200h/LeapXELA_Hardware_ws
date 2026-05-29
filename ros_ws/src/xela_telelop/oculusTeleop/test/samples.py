from sensor_msgs.msg import JointState


def get_unordered_joint_state_message_with_index_as_joint_value():
    msg = JointState()
    msg.name = [
        'if_mcp', 'if_rot', 'if_pip', 'if_dip',
        'mf_mcp', 'mf_rot', 'mf_pip', 'mf_dip',
        'rf_mcp', 'rf_rot', 'rf_pip', 'rf_dip',
        'th_cmc', 'th_axl', 'th_mcp', 'th_ipl'] 
    msg.position = [
        float(i) for i in [4,6,5,7,
        8,10,9,11,
        12,14,13,15,
        0,1,2,3]
    ]   

    return msg

def get_ordered_joint_state_message_with_index_as_joint_value():
    msg = JointState()
    msg.name = [
     'th_cmc', 'th_axl', 'th_mcp', 'th_ipl',
     'if_mcp', 'if_pip', 'if_rot', 'if_dip', 
     'mf_mcp', 'mf_pip', 'mf_rot', 'mf_dip',
     'rf_mcp', 'rf_pip', 'rf_rot', 'rf_dip']
    msg.position = [
    
        float(i) for i in [0,1,2,3,
        4,5,6,7,    
        8,9,10,11,
        12,13,14,15]
    ]
    return msg


def get_joint_ranges_hw():
    return {
        "ll":  [
            135, 5, 110, 115,
            275, 195, 200, 185,
            275, 195, 200, 185,
            275, 195, 200, 185
        ],
        "ul":[
            305,205,10,15,
            145,60,160,50,
            145,60,160,50,
            145,60,160,50,
        ]
    }

def get_joint_ranges_sim():
    return {
        "ll": [
            -0.785,  -0.305, -0.262, -0.436,
            -0.1745, -0.262, -0.349, -0.0873,
            -0.1745, -0.262, -0.349, -0.0873,
            -0.1745, -0.262, -0.349, -0.0873
        ],
        "ul": [
            2.181, 0.436, 1.396, 1.309,
            2.0944,2.0944,0.349, 2.2689,
            2.0944,2.0944,0.349, 2.2689,
            2.0944,2.0944,0.349, 2.2689
        ]
    }

def get_hardware_joints_at_zero_position():

    return [
        180, 180,  95,  90,
        265,180,180,180,
        265,180,180,180,
        265,180,180,180
    ]