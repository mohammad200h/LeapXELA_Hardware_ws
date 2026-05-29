// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice
#include "xela_point_cloud_representation/msg/detail/hand_sensors__rosidl_typesupport_fastrtps_cpp.hpp"
#include "xela_point_cloud_representation/msg/detail/hand_sensors__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions
namespace xela_point_cloud_representation
{
namespace msg
{
namespace typesupport_fastrtps_cpp
{
bool cdr_serialize(
  const xela_point_cloud_representation::msg::Texel &,
  eprosima::fastcdr::Cdr &);
bool cdr_deserialize(
  eprosima::fastcdr::Cdr &,
  xela_point_cloud_representation::msg::Texel &);
size_t get_serialized_size(
  const xela_point_cloud_representation::msg::Texel &,
  size_t current_alignment);
size_t
max_serialized_size_Texel(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);
}  // namespace typesupport_fastrtps_cpp
}  // namespace msg
}  // namespace xela_point_cloud_representation


namespace xela_point_cloud_representation
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation
cdr_serialize(
  const xela_point_cloud_representation::msg::HandSensors & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: texels
  {
    size_t size = ros_message.texels.size();
    cdr << static_cast<uint32_t>(size);
    for (size_t i = 0; i < size; i++) {
      xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::cdr_serialize(
        ros_message.texels[i],
        cdr);
    }
  }
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  xela_point_cloud_representation::msg::HandSensors & ros_message)
{
  // Member: texels
  {
    uint32_t cdrSize;
    cdr >> cdrSize;
    size_t size = static_cast<size_t>(cdrSize);

    // Check there are at least 'size' remaining bytes in the CDR stream before resizing
    auto old_state = cdr.getState();
    bool correct_size = cdr.jump(size);
    cdr.setState(old_state);
    if (!correct_size) {
      fprintf(stderr, "sequence size exceeds remaining buffer\n");
      return false;
    }

    ros_message.texels.resize(size);
    for (size_t i = 0; i < size; i++) {
      xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::cdr_deserialize(
        cdr, ros_message.texels[i]);
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation
get_serialized_size(
  const xela_point_cloud_representation::msg::HandSensors & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: texels
  {
    size_t array_size = ros_message.texels.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    for (size_t index = 0; index < array_size; ++index) {
      current_alignment +=
        xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::get_serialized_size(
        ros_message.texels[index], current_alignment);
    }
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_point_cloud_representation
max_serialized_size_HandSensors(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;


  // Member: texels
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);


    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size =
        xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::max_serialized_size_Texel(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = xela_point_cloud_representation::msg::HandSensors;
    is_plain =
      (
      offsetof(DataType, texels) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _HandSensors__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const xela_point_cloud_representation::msg::HandSensors *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _HandSensors__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<xela_point_cloud_representation::msg::HandSensors *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _HandSensors__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const xela_point_cloud_representation::msg::HandSensors *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _HandSensors__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_HandSensors(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _HandSensors__callbacks = {
  "xela_point_cloud_representation::msg",
  "HandSensors",
  _HandSensors__cdr_serialize,
  _HandSensors__cdr_deserialize,
  _HandSensors__get_serialized_size,
  _HandSensors__max_serialized_size
};

static rosidl_message_type_support_t _HandSensors__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_HandSensors__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace xela_point_cloud_representation

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_point_cloud_representation
const rosidl_message_type_support_t *
get_message_type_support_handle<xela_point_cloud_representation::msg::HandSensors>()
{
  return &xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::_HandSensors__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, xela_point_cloud_representation, msg, HandSensors)() {
  return &xela_point_cloud_representation::msg::typesupport_fastrtps_cpp::_HandSensors__handle;
}

#ifdef __cplusplus
}
#endif
