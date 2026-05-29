// generated from rosidl_generator_cpp/resource/rosidl_generator_cpp__visibility_control.hpp.in
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_GENERATOR_CPP__VISIBILITY_CONTROL_HPP_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_GENERATOR_CPP__VISIBILITY_CONTROL_HPP_

#ifdef __cplusplus
extern "C"
{
#endif

// This logic was borrowed (then namespaced) from the examples on the gcc wiki:
//     https://gcc.gnu.org/wiki/Visibility

#if defined _WIN32 || defined __CYGWIN__
  #ifdef __GNUC__
    #define ROSIDL_GENERATOR_CPP_EXPORT_xela_point_cloud_representation __attribute__ ((dllexport))
    #define ROSIDL_GENERATOR_CPP_IMPORT_xela_point_cloud_representation __attribute__ ((dllimport))
  #else
    #define ROSIDL_GENERATOR_CPP_EXPORT_xela_point_cloud_representation __declspec(dllexport)
    #define ROSIDL_GENERATOR_CPP_IMPORT_xela_point_cloud_representation __declspec(dllimport)
  #endif
  #ifdef ROSIDL_GENERATOR_CPP_BUILDING_DLL_xela_point_cloud_representation
    #define ROSIDL_GENERATOR_CPP_PUBLIC_xela_point_cloud_representation ROSIDL_GENERATOR_CPP_EXPORT_xela_point_cloud_representation
  #else
    #define ROSIDL_GENERATOR_CPP_PUBLIC_xela_point_cloud_representation ROSIDL_GENERATOR_CPP_IMPORT_xela_point_cloud_representation
  #endif
#else
  #define ROSIDL_GENERATOR_CPP_EXPORT_xela_point_cloud_representation __attribute__ ((visibility("default")))
  #define ROSIDL_GENERATOR_CPP_IMPORT_xela_point_cloud_representation
  #if __GNUC__ >= 4
    #define ROSIDL_GENERATOR_CPP_PUBLIC_xela_point_cloud_representation __attribute__ ((visibility("default")))
  #else
    #define ROSIDL_GENERATOR_CPP_PUBLIC_xela_point_cloud_representation
  #endif
#endif

#ifdef __cplusplus
}
#endif

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_GENERATOR_CPP__VISIBILITY_CONTROL_HPP_
