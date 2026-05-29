// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "xela_point_cloud_representation/msg/detail/hand_sensors__rosidl_typesupport_introspection_c.h"
#include "xela_point_cloud_representation/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "xela_point_cloud_representation/msg/detail/hand_sensors__functions.h"
#include "xela_point_cloud_representation/msg/detail/hand_sensors__struct.h"


// Include directives for member types
// Member `texels`
#include "xela_point_cloud_representation/msg/texel.h"
// Member `texels`
#include "xela_point_cloud_representation/msg/detail/texel__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  xela_point_cloud_representation__msg__HandSensors__init(message_memory);
}

void xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_fini_function(void * message_memory)
{
  xela_point_cloud_representation__msg__HandSensors__fini(message_memory);
}

size_t xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__size_function__HandSensors__texels(
  const void * untyped_member)
{
  const xela_point_cloud_representation__msg__Texel__Sequence * member =
    (const xela_point_cloud_representation__msg__Texel__Sequence *)(untyped_member);
  return member->size;
}

const void * xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_const_function__HandSensors__texels(
  const void * untyped_member, size_t index)
{
  const xela_point_cloud_representation__msg__Texel__Sequence * member =
    (const xela_point_cloud_representation__msg__Texel__Sequence *)(untyped_member);
  return &member->data[index];
}

void * xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_function__HandSensors__texels(
  void * untyped_member, size_t index)
{
  xela_point_cloud_representation__msg__Texel__Sequence * member =
    (xela_point_cloud_representation__msg__Texel__Sequence *)(untyped_member);
  return &member->data[index];
}

void xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__fetch_function__HandSensors__texels(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const xela_point_cloud_representation__msg__Texel * item =
    ((const xela_point_cloud_representation__msg__Texel *)
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_const_function__HandSensors__texels(untyped_member, index));
  xela_point_cloud_representation__msg__Texel * value =
    (xela_point_cloud_representation__msg__Texel *)(untyped_value);
  *value = *item;
}

void xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__assign_function__HandSensors__texels(
  void * untyped_member, size_t index, const void * untyped_value)
{
  xela_point_cloud_representation__msg__Texel * item =
    ((xela_point_cloud_representation__msg__Texel *)
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_function__HandSensors__texels(untyped_member, index));
  const xela_point_cloud_representation__msg__Texel * value =
    (const xela_point_cloud_representation__msg__Texel *)(untyped_value);
  *item = *value;
}

bool xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__resize_function__HandSensors__texels(
  void * untyped_member, size_t size)
{
  xela_point_cloud_representation__msg__Texel__Sequence * member =
    (xela_point_cloud_representation__msg__Texel__Sequence *)(untyped_member);
  xela_point_cloud_representation__msg__Texel__Sequence__fini(member);
  return xela_point_cloud_representation__msg__Texel__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_member_array[1] = {
  {
    "texels",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(xela_point_cloud_representation__msg__HandSensors, texels),  // bytes offset in struct
    NULL,  // default value
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__size_function__HandSensors__texels,  // size() function pointer
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_const_function__HandSensors__texels,  // get_const(index) function pointer
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__get_function__HandSensors__texels,  // get(index) function pointer
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__fetch_function__HandSensors__texels,  // fetch(index, &value) function pointer
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__assign_function__HandSensors__texels,  // assign(index, value) function pointer
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__resize_function__HandSensors__texels  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_members = {
  "xela_point_cloud_representation__msg",  // message namespace
  "HandSensors",  // message name
  1,  // number of fields
  sizeof(xela_point_cloud_representation__msg__HandSensors),
  xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_member_array,  // message members
  xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_init_function,  // function to initialize message memory (memory has to be allocated)
  xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_type_support_handle = {
  0,
  &xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_xela_point_cloud_representation
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, xela_point_cloud_representation, msg, HandSensors)() {
  xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, xela_point_cloud_representation, msg, Texel)();
  if (!xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_type_support_handle.typesupport_identifier) {
    xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &xela_point_cloud_representation__msg__HandSensors__rosidl_typesupport_introspection_c__HandSensors_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
