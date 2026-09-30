# Target a flex vertex by body name and/or hardware taxel id.
# If flex_vertex_id is non-empty it is used; otherwise taxel_id is used.
# Force is interpreted in the taxel-local body frame by default
# (configurable via process_hand_sensors_into_pointcloud parameter
# taxel_perturbation_local_frame).
string flex_vertex_id
int32 taxel_id
float32[3] force
