// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "xela_point_cloud_representation/msg/detail/hand_sensors__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace xela_point_cloud_representation
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void HandSensors_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) xela_point_cloud_representation::msg::HandSensors(_init);
}

void HandSensors_fini_function(void * message_memory)
{
  auto typed_message = static_cast<xela_point_cloud_representation::msg::HandSensors *>(message_memory);
  typed_message->~HandSensors();
}

size_t size_function__HandSensors__texels(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<xela_point_cloud_representation::msg::Texel> *>(untyped_member);
  return member->size();
}

const void * get_const_function__HandSensors__texels(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<xela_point_cloud_representation::msg::Texel> *>(untyped_member);
  return &member[index];
}

void * get_function__HandSensors__texels(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<xela_point_cloud_representation::msg::Texel> *>(untyped_member);
  return &member[index];
}

void fetch_function__HandSensors__texels(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const xela_point_cloud_representation::msg::Texel *>(
    get_const_function__HandSensors__texels(untyped_member, index));
  auto & value = *reinterpret_cast<xela_point_cloud_representation::msg::Texel *>(untyped_value);
  value = item;
}

void assign_function__HandSensors__texels(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<xela_point_cloud_representation::msg::Texel *>(
    get_function__HandSensors__texels(untyped_member, index));
  const auto & value = *reinterpret_cast<const xela_point_cloud_representation::msg::Texel *>(untyped_value);
  item = value;
}

void resize_function__HandSensors__texels(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<xela_point_cloud_representation::msg::Texel> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember HandSensors_message_member_array[1] = {
  {
    "texels",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<xela_point_cloud_representation::msg::Texel>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(xela_point_cloud_representation::msg::HandSensors, texels),  // bytes offset in struct
    nullptr,  // default value
    size_function__HandSensors__texels,  // size() function pointer
    get_const_function__HandSensors__texels,  // get_const(index) function pointer
    get_function__HandSensors__texels,  // get(index) function pointer
    fetch_function__HandSensors__texels,  // fetch(index, &value) function pointer
    assign_function__HandSensors__texels,  // assign(index, value) function pointer
    resize_function__HandSensors__texels  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers HandSensors_message_members = {
  "xela_point_cloud_representation::msg",  // message namespace
  "HandSensors",  // message name
  1,  // number of fields
  sizeof(xela_point_cloud_representation::msg::HandSensors),
  HandSensors_message_member_array,  // message members
  HandSensors_init_function,  // function to initialize message memory (memory has to be allocated)
  HandSensors_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t HandSensors_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &HandSensors_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace xela_point_cloud_representation


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<xela_point_cloud_representation::msg::HandSensors>()
{
  return &::xela_point_cloud_representation::msg::rosidl_typesupport_introspection_cpp::HandSensors_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, xela_point_cloud_representation, msg, HandSensors)() {
  return &::xela_point_cloud_representation::msg::rosidl_typesupport_introspection_cpp::HandSensors_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
