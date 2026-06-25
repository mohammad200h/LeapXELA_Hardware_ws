// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "arm_server/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "arm_server/msg/detail/scene_object__struct.hpp"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

#include "fastcdr/Cdr.h"

namespace arm_server
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_arm_server
cdr_serialize(
  const arm_server::msg::SceneObject & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_arm_server
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  arm_server::msg::SceneObject & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_arm_server
get_serialized_size(
  const arm_server::msg::SceneObject & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_arm_server
max_serialized_size_SceneObject(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_arm_server
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, arm_server, msg, SceneObject)();

#ifdef __cplusplus
}
#endif

#endif  // ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
