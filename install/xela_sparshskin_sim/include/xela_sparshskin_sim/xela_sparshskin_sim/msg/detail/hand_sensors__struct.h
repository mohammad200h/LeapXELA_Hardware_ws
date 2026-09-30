// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from xela_sparshskin_sim:msg/HandSensors.idl
// generated code does not contain a copyright notice

#ifndef XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__STRUCT_H_
#define XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__STRUCT_H_

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
#include "xela_sparshskin_sim/msg/detail/texel__struct.h"

/// Struct defined in msg/HandSensors in the package xela_sparshskin_sim.
typedef struct xela_sparshskin_sim__msg__HandSensors
{
  xela_sparshskin_sim__msg__Texel__Sequence texels;
} xela_sparshskin_sim__msg__HandSensors;

// Struct for a sequence of xela_sparshskin_sim__msg__HandSensors.
typedef struct xela_sparshskin_sim__msg__HandSensors__Sequence
{
  xela_sparshskin_sim__msg__HandSensors * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} xela_sparshskin_sim__msg__HandSensors__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__STRUCT_H_
