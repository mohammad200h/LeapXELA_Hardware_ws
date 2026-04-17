# Collect data by running leaphand_node individually, motors disabled.
ros2 launch leap_hand launch_leap.py \
    ros__params:="
        {
            'leaphand_node': {
                'collect_data': true,
                'data_collection_name': '$1',
                'data_collection_repeats': 10
            }
        }"

# Save data in repo as data/ with cli input name
# Reenable leaphand_node functions, stream position_node
# Collect for 10 repeatss
