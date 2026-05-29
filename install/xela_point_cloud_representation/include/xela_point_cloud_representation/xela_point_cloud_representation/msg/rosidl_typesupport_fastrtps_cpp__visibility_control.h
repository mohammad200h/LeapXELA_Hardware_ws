// generated from
// rosidl_typesupport_fastrtps_cpp/resource/rosidl_typesupport_fastrtps_cpp__visibility_control.h.in
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_TYPESUPPORT_FASTRTPS_CPP__VISIBILITY_CONTROL_H_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_TYPESUPPORT_FASTRTPS_CPP__VISIBILITY_CONTROL_H_

#if __cplusplus
extern "C"
{
#endif

// This logic was borrowed (then namespaced) from the examples on the gcc wiki:
//     https://gcc.gnu.org/wiki/Visibility

#if defined _WIN32 || defined __CYGWIN__
  #ifdef __GNUC__
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_point_cloud_representation __attribute__ ((dllexport))
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_IMPORT_xela_point_cloud_representation __attribute__ ((dllimport))
  #else
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_point_cloud_representation __declspec(dllexport)
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_IMPORT_xela_point_cloud_representation __declspec(dllimport)
  #endif
  #ifdef ROSIDL_TYPESUPPORT_FASTRTPS_CPP_BUILDING_DLL_xela_point_cloud_representation
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_point_cloud_representation
  #else
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation ROSIDL_TYPESUPPORT_FASTRTPS_CPP_IMPORT_xela_point_cloud_representation
  #endif
#else
  #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_point_cloud_representation __attribute__ ((visibility("default")))
  #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_IMPORT_xela_point_cloud_representation
  #if __GNUC__ >= 4
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation __attribute__ ((visibility("default")))
  #else
    #define ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation
  #endif
#endif

#if __cplusplus
}
#endif

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__ROSIDL_TYPESUPPORT_FASTRTPS_CPP__VISIBILITY_CONTROL_H_
