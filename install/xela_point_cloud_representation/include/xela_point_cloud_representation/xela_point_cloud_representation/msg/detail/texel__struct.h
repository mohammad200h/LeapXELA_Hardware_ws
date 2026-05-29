// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_H_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'sensor_name'
// Member 'joint_x'
// Member 'joint_y'
// Member 'joint_z'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/Texel in the package xela_point_cloud_representation.
typedef struct xela_point_cloud_representation__msg__Texel
{
  int32_t taxel_id;
  rosidl_runtime_c__String sensor_name;
  float x;
  float y;
  float z;
  rosidl_runtime_c__String joint_x;
  rosidl_runtime_c__String joint_y;
  rosidl_runtime_c__String joint_z;
} xela_point_cloud_representation__msg__Texel;

// Struct for a sequence of xela_point_cloud_representation__msg__Texel.
typedef struct xela_point_cloud_representation__msg__Texel__Sequence
{
  xela_point_cloud_representation__msg__Texel * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} xela_point_cloud_representation__msg__Texel__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_H_
