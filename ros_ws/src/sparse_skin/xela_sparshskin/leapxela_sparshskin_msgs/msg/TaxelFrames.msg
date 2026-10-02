# Forward-kinematics poses of the Leap/Xela taxels and their contact forces.
# Entries follow the FK flatten order (XELA_FLATTEN_ORDER in fk_taxels); N = 368.

std_msgs/Header header

# Hardware taxel id and tactile patch index of each entry, length N.
int32[] taxel_ids
uint8[] patch_ids

# Taxel positions in header.frame_id, row-major (N, 3).
float32[] positions
# Sensor-local -> header.frame_id rotation matrices, row-major (N, 3, 3).
float32[] rotations

# Contact forces, row-major (N, 3). Empty until HandSensors data has been received.
float32[] forces_world
float32[] forces_local
