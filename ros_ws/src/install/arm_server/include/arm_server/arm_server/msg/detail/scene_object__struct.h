// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_H_
#define ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'id'
// Member 'shape_type'
#include "rosidl_runtime_c/string.h"
// Member 'dimensions'
#include "rosidl_runtime_c/primitives_sequence.h"

/// Struct defined in msg/SceneObject in the package arm_server.
/**
  * Collision object to add to the MoveIt planning scene.
 */
typedef struct arm_server__msg__SceneObject
{
  rosidl_runtime_c__String id;
  rosidl_runtime_c__String shape_type;
  rosidl_runtime_c__double__Sequence dimensions;
  double x;
  double y;
  double z;
  double roll;
  double pitch;
  double yaw;
  bool use_color;
  float color_r;
  float color_g;
  float color_b;
  float color_a;
} arm_server__msg__SceneObject;

// Struct for a sequence of arm_server__msg__SceneObject.
typedef struct arm_server__msg__SceneObject__Sequence
{
  arm_server__msg__SceneObject * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__msg__SceneObject__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_H_
