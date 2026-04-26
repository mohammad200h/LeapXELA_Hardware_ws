# Install script for directory: /workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src

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

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/lib/libccd.a")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ccd" TYPE FILE FILES
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src/ccd/ccd.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src/ccd/compiler.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src/ccd/ccd_export.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src/ccd/quat.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-src/src/ccd/vec3.h"
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-build/src/ccd/config.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/ccd/ccd-targets.cmake")
    file(DIFFERENT EXPORT_FILE_CHANGED FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/ccd/ccd-targets.cmake"
         "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-build/src/CMakeFiles/Export/lib/ccd/ccd-targets.cmake")
    if(EXPORT_FILE_CHANGED)
      file(GLOB OLD_CONFIG_FILES "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/ccd/ccd-targets-*.cmake")
      if(OLD_CONFIG_FILES)
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/ccd/ccd-targets.cmake\" will be replaced.  Removing files [${OLD_CONFIG_FILES}].")
        file(REMOVE ${OLD_CONFIG_FILES})
      endif()
    endif()
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/ccd" TYPE FILE FILES "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-build/src/CMakeFiles/Export/lib/ccd/ccd-targets.cmake")
  if("${CMAKE_INSTALL_CONFIG_NAME}" MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/ccd" TYPE FILE FILES "/workspace/LeapXELA_Hardware_ws/ros_ws/src/build/xela_point_cloud_representation/_deps/ccd-build/src/CMakeFiles/Export/lib/ccd/ccd-targets-release.cmake")
  endif()
endif()

