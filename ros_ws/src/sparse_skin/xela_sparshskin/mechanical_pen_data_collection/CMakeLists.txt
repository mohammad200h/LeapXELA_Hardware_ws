cmake_minimum_required(VERSION 3.8)
project(mechanical_pen_data_collection)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(mujoco REQUIRED)
find_package(glfw3 REQUIRED)

# C++ MuJoCo simulation node
add_executable(mujoco_sim_node ${PROJECT_NAME}/mujoco_sim_node.cpp)
ament_target_dependencies(mujoco_sim_node ament_index_cpp rclcpp sensor_msgs std_msgs)
target_link_libraries(mujoco_sim_node mujoco::mujoco glfw)
install(TARGETS mujoco_sim_node DESTINATION lib/${PROJECT_NAME})

# Python package and its console scripts
ament_python_install_package(${PROJECT_NAME})

set(PYTHON_ENTRY_POINTS
  "rosbag_recorder:rosbag_recorder"
  "bag_viewer:bag_viewer"
  "record_demonstration:record_demonstration"
  "analyze_playback:analyze_playback"
  "label_playbacks:label_playbacks"
  "label_click_press:click_press_labels"
  "sparsh_skin_transformation:sparsh_skin_transformation"
  "hand_ik:hand_ik"
)
foreach(entry ${PYTHON_ENTRY_POINTS})
  string(REPLACE ":" ";" entry ${entry})
  list(GET entry 0 script_name)
  list(GET entry 1 module_name)
  set(script ${CMAKE_CURRENT_BINARY_DIR}/scripts/${script_name})
  file(WRITE ${script}
    "#!/usr/bin/env python3\n"
    "import sys\n"
    "from ${PROJECT_NAME}.${module_name} import main\n"
    "sys.exit(main())\n")
  install(PROGRAMS ${script} DESTINATION lib/${PROJECT_NAME})
endforeach()

install(FILES ${PROJECT_NAME}/events.json DESTINATION share/${PROJECT_NAME})
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch
  FILES_MATCHING PATTERN "*.py" PATTERN "__pycache__" EXCLUDE)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(${PROJECT_NAME}_pytest test TIMEOUT 300)
endif()

ament_package()
