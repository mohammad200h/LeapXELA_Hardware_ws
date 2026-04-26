// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from xela_server_ros2:msg/SensorFull.idl
// generated code does not contain a copyright notice
#include "xela_server_ros2/msg/detail/sensor_full__rosidl_typesupport_fastrtps_cpp.hpp"
#include "xela_server_ros2/msg/detail/sensor_full__struct.hpp"

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
namespace xela_server_ros2
{
namespace msg
{
namespace typesupport_fastrtps_cpp
{
bool cdr_serialize(
  const xela_server_ros2::msg::Taxel &,
  eprosima::fastcdr::Cdr &);
bool cdr_deserialize(
  eprosima::fastcdr::Cdr &,
  xela_server_ros2::msg::Taxel &);
size_t get_serialized_size(
  const xela_server_ros2::msg::Taxel &,
  size_t current_alignment);
size_t
max_serialized_size_Taxel(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);
}  // namespace typesupport_fastrtps_cpp
}  // namespace msg
}  // namespace xela_server_ros2

namespace xela_server_ros2
{
namespace msg
{
namespace typesupport_fastrtps_cpp
{
bool cdr_serialize(
  const xela_server_ros2::msg::Forces &,
  eprosima::fastcdr::Cdr &);
bool cdr_deserialize(
  eprosima::fastcdr::Cdr &,
  xela_server_ros2::msg::Forces &);
size_t get_serialized_size(
  const xela_server_ros2::msg::Forces &,
  size_t current_alignment);
size_t
max_serialized_size_Forces(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);
}  // namespace typesupport_fastrtps_cpp
}  // namespace msg
}  // namespace xela_server_ros2


namespace xela_server_ros2
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_server_ros2
cdr_serialize(
  const xela_server_ros2::msg::SensorFull & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: message
  cdr << ros_message.message;
  // Member: time
  cdr << ros_message.time;
  // Member: model
  cdr << ros_message.model;
  // Member: sensor_pos
  cdr << ros_message.sensor_pos;
  // Member: taxels
  {
    size_t size = ros_message.taxels.size();
    cdr << static_cast<uint32_t>(size);
    for (size_t i = 0; i < size; i++) {
      xela_server_ros2::msg::typesupport_fastrtps_cpp::cdr_serialize(
        ros_message.taxels[i],
        cdr);
    }
  }
  // Member: forces
  {
    size_t size = ros_message.forces.size();
    cdr << static_cast<uint32_t>(size);
    for (size_t i = 0; i < size; i++) {
      xela_server_ros2::msg::typesupport_fastrtps_cpp::cdr_serialize(
        ros_message.forces[i],
        cdr);
    }
  }
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_server_ros2
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  xela_server_ros2::msg::SensorFull & ros_message)
{
  // Member: message
  cdr >> ros_message.message;

  // Member: time
  cdr >> ros_message.time;

  // Member: model
  cdr >> ros_message.model;

  // Member: sensor_pos
  cdr >> ros_message.sensor_pos;

  // Member: taxels
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

    ros_message.taxels.resize(size);
    for (size_t i = 0; i < size; i++) {
      xela_server_ros2::msg::typesupport_fastrtps_cpp::cdr_deserialize(
        cdr, ros_message.taxels[i]);
    }
  }

  // Member: forces
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

    ros_message.forces.resize(size);
    for (size_t i = 0; i < size; i++) {
      xela_server_ros2::msg::typesupport_fastrtps_cpp::cdr_deserialize(
        cdr, ros_message.forces[i]);
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_server_ros2
get_serialized_size(
  const xela_server_ros2::msg::SensorFull & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: message
  {
    size_t item_size = sizeof(ros_message.message);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: time
  {
    size_t item_size = sizeof(ros_message.time);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: model
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message.model.size() + 1);
  // Member: sensor_pos
  {
    size_t item_size = sizeof(ros_message.sensor_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: taxels
  {
    size_t array_size = ros_message.taxels.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    for (size_t index = 0; index < array_size; ++index) {
      current_alignment +=
        xela_server_ros2::msg::typesupport_fastrtps_cpp::get_serialized_size(
        ros_message.taxels[index], current_alignment);
    }
  }
  // Member: forces
  {
    size_t array_size = ros_message.forces.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    for (size_t index = 0; index < array_size; ++index) {
      current_alignment +=
        xela_server_ros2::msg::typesupport_fastrtps_cpp::get_serialized_size(
        ros_message.forces[index], current_alignment);
    }
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_xela_server_ros2
max_serialized_size_SensorFull(
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


  // Member: message
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  // Member: time
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: model
  {
    size_t array_size = 1;

    full_bounded = false;
    is_plain = false;
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        1;
    }
  }

  // Member: sensor_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  // Member: taxels
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
        xela_server_ros2::msg::typesupport_fastrtps_cpp::max_serialized_size_Taxel(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  // Member: forces
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
        xela_server_ros2::msg::typesupport_fastrtps_cpp::max_serialized_size_Forces(
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
    using DataType = xela_server_ros2::msg::SensorFull;
    is_plain =
      (
      offsetof(DataType, forces) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _SensorFull__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const xela_server_ros2::msg::SensorFull *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _SensorFull__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<xela_server_ros2::msg::SensorFull *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _SensorFull__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const xela_server_ros2::msg::SensorFull *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _SensorFull__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_SensorFull(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _SensorFull__callbacks = {
  "xela_server_ros2::msg",
  "SensorFull",
  _SensorFull__cdr_serialize,
  _SensorFull__cdr_deserialize,
  _SensorFull__get_serialized_size,
  _SensorFull__max_serialized_size
};

static rosidl_message_type_support_t _SensorFull__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_SensorFull__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace xela_server_ros2

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_xela_server_ros2
const rosidl_message_type_support_t *
get_message_type_support_handle<xela_server_ros2::msg::SensorFull>()
{
  return &xela_server_ros2::msg::typesupport_fastrtps_cpp::_SensorFull__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, xela_server_ros2, msg, SensorFull)() {
  return &xela_server_ros2::msg::typesupport_fastrtps_cpp::_SensorFull__handle;
}

#ifdef __cplusplus
}
#endif
