cmake_minimum_required(VERSION 3.8)
project(xela_sparshskin_sim)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(glfw3 REQUIRED)
find_package(OpenGL REQUIRED)
find_package(mujoco 3.2.0 REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Texel.msg"
  "msg/HandSensors.msg"
  "msg/TaxelPertubation.msg"
)


add_executable(process_hand_sensors_into_pointcloud
  src/process_hand_sensors_into_pointcloud.cc
  src/camera_control.cc
  src/stickyskin.cc
  src/object.cc
)

target_include_directories(process_hand_sensors_into_pointcloud PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(process_hand_sensors_into_pointcloud
  ament_index_cpp
  rclcpp
  sensor_msgs
)

rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} "rosidl_typesupport_cpp")
target_link_libraries(process_hand_sensors_into_pointcloud
  "${cpp_typesupport_target}"
  mujoco::mujoco
  glfw
  OpenGL::GL
)


install(TARGETS process_hand_sensors_into_pointcloud
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  src/hand_controller.py
  src/leap_taxel_map.py
  src/taxel_pertubation.py
  DESTINATION lib/${PROJECT_NAME}
)

install(FILES
  src/leap_sensor_taxel_map.json
  DESTINATION share/${PROJECT_NAME}
)

# Keep a copy next to the Python scripts as well.
install(FILES
  src/leap_sensor_taxel_map.json
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include/
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(
    test/test_flex_uspa46_3_perturbation.py
    TIMEOUT 120
  )
endif()

ament_package()
