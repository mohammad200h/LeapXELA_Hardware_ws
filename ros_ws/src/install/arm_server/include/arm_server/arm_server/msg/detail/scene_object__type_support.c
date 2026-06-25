// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "arm_server/msg/detail/scene_object__rosidl_typesupport_introspection_c.h"
#include "arm_server/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "arm_server/msg/detail/scene_object__functions.h"
#include "arm_server/msg/detail/scene_object__struct.h"


// Include directives for member types
// Member `id`
// Member `shape_type`
#include "rosidl_runtime_c/string_functions.h"
// Member `dimensions`
#include "rosidl_runtime_c/primitives_sequence_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  arm_server__msg__SceneObject__init(message_memory);
}

void arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_fini_function(void * message_memory)
{
  arm_server__msg__SceneObject__fini(message_memory);
}

size_t arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__size_function__SceneObject__dimensions(
  const void * untyped_member)
{
  const rosidl_runtime_c__double__Sequence * member =
    (const rosidl_runtime_c__double__Sequence *)(untyped_member);
  return member->size;
}

const void * arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_const_function__SceneObject__dimensions(
  const void * untyped_member, size_t index)
{
  const rosidl_runtime_c__double__Sequence * member =
    (const rosidl_runtime_c__double__Sequence *)(untyped_member);
  return &member->data[index];
}

void * arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_function__SceneObject__dimensions(
  void * untyped_member, size_t index)
{
  rosidl_runtime_c__double__Sequence * member =
    (rosidl_runtime_c__double__Sequence *)(untyped_member);
  return &member->data[index];
}

void arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__fetch_function__SceneObject__dimensions(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const double * item =
    ((const double *)
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_const_function__SceneObject__dimensions(untyped_member, index));
  double * value =
    (double *)(untyped_value);
  *value = *item;
}

void arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__assign_function__SceneObject__dimensions(
  void * untyped_member, size_t index, const void * untyped_value)
{
  double * item =
    ((double *)
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_function__SceneObject__dimensions(untyped_member, index));
  const double * value =
    (const double *)(untyped_value);
  *item = *value;
}

bool arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__resize_function__SceneObject__dimensions(
  void * untyped_member, size_t size)
{
  rosidl_runtime_c__double__Sequence * member =
    (rosidl_runtime_c__double__Sequence *)(untyped_member);
  rosidl_runtime_c__double__Sequence__fini(member);
  return rosidl_runtime_c__double__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_member_array[14] = {
  {
    "id",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, id),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "shape_type",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, shape_type),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dimensions",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, dimensions),  // bytes offset in struct
    NULL,  // default value
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__size_function__SceneObject__dimensions,  // size() function pointer
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_const_function__SceneObject__dimensions,  // get_const(index) function pointer
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__get_function__SceneObject__dimensions,  // get(index) function pointer
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__fetch_function__SceneObject__dimensions,  // fetch(index, &value) function pointer
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__assign_function__SceneObject__dimensions,  // assign(index, value) function pointer
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__resize_function__SceneObject__dimensions  // resize(index) function pointer
  },
  {
    "x",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, x),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "y",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, y),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "z",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, z),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "roll",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, roll),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "pitch",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, pitch),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "yaw",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, yaw),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "use_color",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, use_color),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "color_r",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, color_r),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "color_g",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, color_g),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "color_b",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, color_b),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "color_a",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server__msg__SceneObject, color_a),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_members = {
  "arm_server__msg",  // message namespace
  "SceneObject",  // message name
  14,  // number of fields
  sizeof(arm_server__msg__SceneObject),
  arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_member_array,  // message members
  arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_init_function,  // function to initialize message memory (memory has to be allocated)
  arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_type_support_handle = {
  0,
  &arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_arm_server
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, msg, SceneObject)() {
  if (!arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_type_support_handle.typesupport_identifier) {
    arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &arm_server__msg__SceneObject__rosidl_typesupport_introspection_c__SceneObject_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
