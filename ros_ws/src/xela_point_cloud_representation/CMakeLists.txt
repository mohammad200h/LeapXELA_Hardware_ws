cmake_minimum_required(VERSION 3.8)
project(xela_point_cloud_representation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(glfw3 REQUIRED)
find_package(OpenGL REQUIRED)


add_executable(process_hand_sensors_into_pointcloud
  src/process_hand_sensors_into_pointcloud.cc
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

target_link_libraries(process_hand_sensors_into_pointcloud
  dl
  glfw
  OpenGL::GL
)


install(TARGETS process_hand_sensors_into_pointcloud
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  src/hand_controller.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include/
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

ament_package()
