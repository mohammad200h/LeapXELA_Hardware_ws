// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_H_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'texels'
#include "xela_point_cloud_representation/msg/detail/texel__struct.h"

/// Struct defined in msg/HandSensors in the package xela_point_cloud_representation.
typedef struct xela_point_cloud_representation__msg__HandSensors
{
  xela_point_cloud_representation__msg__Texel__Sequence texels;
} xela_point_cloud_representation__msg__HandSensors;

// Struct for a sequence of xela_point_cloud_representation__msg__HandSensors.
typedef struct xela_point_cloud_representation__msg__HandSensors__Sequence
{
  xela_point_cloud_representation__msg__HandSensors * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} xela_point_cloud_representation__msg__HandSensors__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_H_
