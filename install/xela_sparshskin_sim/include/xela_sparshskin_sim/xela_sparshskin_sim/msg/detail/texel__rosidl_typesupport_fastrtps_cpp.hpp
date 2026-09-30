// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from xela_sparshskin_sim:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_SPARSHSKIN_SIM__MSG__DETAIL__TEXEL__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define XELA_SPARSHSKIN_SIM__MSG__DETAIL__TEXEL__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "xela_sparshskin_sim/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "xela_sparshskin_sim/msg/detail/texel__struct.hpp"

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

namespace xela_sparshskin_sim
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_sparshskin_sim
cdr_serialize(
  const xela_sparshskin_sim::msg::Texel & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_sparshskin_sim
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  xela_sparshskin_sim::msg::Texel & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_sparshskin_sim
get_serialized_size(
  const xela_sparshskin_sim::msg::Texel & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_sparshskin_sim
max_serialized_size_Texel(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace xela_sparshskin_sim

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_sparshskin_sim
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, xela_sparshskin_sim, msg, Texel)();

#ifdef __cplusplus
}
#endif

#endif  // XELA_SPARSHSKIN_SIM__MSG__DETAIL__TEXEL__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
