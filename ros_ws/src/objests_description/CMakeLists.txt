cmake_minimum_required(VERSION 3.8)
project(objests_description LANGUAGES C)

if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(OpenGL_GL_PREFERENCE GLVND)

find_package(ament_cmake REQUIRED)
find_package(rcl REQUIRED)
find_package(rcutils REQUIRED)
find_package(mujoco 3.2.0 REQUIRED)
find_package(glfw3 REQUIRED)
find_package(OpenGL REQUIRED)

add_executable(plane_scene_node
  src/plane_scene_node.c
  src/object.c
)
target_include_directories(plane_scene_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
install(DIRECTORY include/
  DESTINATION include
)
ament_target_dependencies(plane_scene_node
  rcl
  rcutils
)
target_link_libraries(plane_scene_node
  mujoco::mujoco
  glfw
  OpenGL::GL
  m
)

install(TARGETS plane_scene_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY mjcf urdf launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
