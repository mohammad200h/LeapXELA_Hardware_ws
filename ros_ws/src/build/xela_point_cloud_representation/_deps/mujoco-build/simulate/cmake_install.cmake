# Install script for directory: /workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/workspace/LeapXELA_Hardware_ws/ros_ws/src/install/xela_point_cloud_representation")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xsimulatex" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE EXECUTABLE FILES "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/bin/simulate")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/simulate" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/simulate")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/simulate")
    endif()
  endif()
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xsimulatex" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/lib/libsimulate.a")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xsimulatex" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/simulate" TYPE FILE FILES
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/simulate.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/platform_ui_adapter.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/glfw_adapter.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/glfw_dispatch.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/glfw_corevideo.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/mujoco-src/simulate/array_safety.h"
    )
endif()

