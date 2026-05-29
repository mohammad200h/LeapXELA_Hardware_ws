// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice
#include "xela_point_cloud_representation/msg/detail/texel__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "xela_point_cloud_representation/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "xela_point_cloud_representation/msg/detail/texel__struct.h"
#include "xela_point_cloud_representation/msg/detail/texel__functions.h"
#include "fastcdr/Cdr.h"

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

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif

#include "rosidl_runtime_c/string.h"  // joint_x, joint_y, joint_z, sensor_name
#include "rosidl_runtime_c/string_functions.h"  // joint_x, joint_y, joint_z, sensor_name

// forward declare type support functions


using _Texel__ros_msg_type = xela_point_cloud_representation__msg__Texel;

static bool _Texel__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _Texel__ros_msg_type * ros_message = static_cast<const _Texel__ros_msg_type *>(untyped_ros_message);
  // Field name: taxel_id
  {
    cdr << ros_message->taxel_id;
  }

  // Field name: sensor_name
  {
    const rosidl_runtime_c__String * str = &ros_message->sensor_name;
    if (str->capacity == 0 || str->capacity <= str->size) {
      fprintf(stderr, "string capacity not greater than size\n");
      return false;
    }
    if (str->data[str->size] != '\0') {
      fprintf(stderr, "string not null-terminated\n");
      return false;
    }
    cdr << str->data;
  }

  // Field name: x
  {
    cdr << ros_message->x;
  }

  // Field name: y
  {
    cdr << ros_message->y;
  }

  // Field name: z
  {
    cdr << ros_message->z;
  }

  // Field name: joint_x
  {
    const rosidl_runtime_c__String * str = &ros_message->joint_x;
    if (str->capacity == 0 || str->capacity <= str->size) {
      fprintf(stderr, "string capacity not greater than size\n");
      return false;
    }
    if (str->data[str->size] != '\0') {
      fprintf(stderr, "string not null-terminated\n");
      return false;
    }
    cdr << str->data;
  }

  // Field name: joint_y
  {
    const rosidl_runtime_c__String * str = &ros_message->joint_y;
    if (str->capacity == 0 || str->capacity <= str->size) {
      fprintf(stderr, "string capacity not greater than size\n");
      return false;
    }
    if (str->data[str->size] != '\0') {
      fprintf(stderr, "string not null-terminated\n");
      return false;
    }
    cdr << str->data;
  }

  // Field name: joint_z
  {
    const rosidl_runtime_c__String * str = &ros_message->joint_z;
    if (str->capacity == 0 || str->capacity <= str->size) {
      fprintf(stderr, "string capacity not greater than size\n");
      return false;
    }
    if (str->data[str->size] != '\0') {
      fprintf(stderr, "string not null-terminated\n");
      return false;
    }
    cdr << str->data;
  }

  return true;
}

static bool _Texel__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _Texel__ros_msg_type * ros_message = static_cast<_Texel__ros_msg_type *>(untyped_ros_message);
  // Field name: taxel_id
  {
    cdr >> ros_message->taxel_id;
  }

  // Field name: sensor_name
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->sensor_name.data) {
      rosidl_runtime_c__String__init(&ros_message->sensor_name);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->sensor_name,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'sensor_name'\n");
      return false;
    }
  }

  // Field name: x
  {
    cdr >> ros_message->x;
  }

  // Field name: y
  {
    cdr >> ros_message->y;
  }

  // Field name: z
  {
    cdr >> ros_message->z;
  }

  // Field name: joint_x
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->joint_x.data) {
      rosidl_runtime_c__String__init(&ros_message->joint_x);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->joint_x,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'joint_x'\n");
      return false;
    }
  }

  // Field name: joint_y
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->joint_y.data) {
      rosidl_runtime_c__String__init(&ros_message->joint_y);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->joint_y,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'joint_y'\n");
      return false;
    }
  }

  // Field name: joint_z
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->joint_z.data) {
      rosidl_runtime_c__String__init(&ros_message->joint_z);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->joint_z,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'joint_z'\n");
      return false;
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_xela_point_cloud_representation
size_t get_serialized_size_xela_point_cloud_representation__msg__Texel(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _Texel__ros_msg_type * ros_message = static_cast<const _Texel__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name taxel_id
  {
    size_t item_size = sizeof(ros_message->taxel_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name sensor_name
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->sensor_name.size + 1);
  // field.name x
  {
    size_t item_size = sizeof(ros_message->x);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name y
  {
    size_t item_size = sizeof(ros_message->y);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name z
  {
    size_t item_size = sizeof(ros_message->z);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name joint_x
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->joint_x.size + 1);
  // field.name joint_y
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->joint_y.size + 1);
  // field.name joint_z
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->joint_z.size + 1);

  return current_alignment - initial_alignment;
}

static uint32_t _Texel__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_xela_point_cloud_representation__msg__Texel(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_xela_point_cloud_representation
size_t max_serialized_size_xela_point_cloud_representation__msg__Texel(
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

  // member: taxel_id
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: sensor_name
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
  // member: x
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: y
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: z
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: joint_x
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
  // member: joint_y
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
  // member: joint_z
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

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = xela_point_cloud_representation__msg__Texel;
    is_plain =
      (
      offsetof(DataType, joint_z) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _Texel__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_xela_point_cloud_representation__msg__Texel(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_Texel = {
  "xela_point_cloud_representation::msg",
  "Texel",
  _Texel__cdr_serialize,
  _Texel__cdr_deserialize,
  _Texel__get_serialized_size,
  _Texel__max_serialized_size
};

static rosidl_message_type_support_t _Texel__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_Texel,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, xela_point_cloud_representation, msg, Texel)() {
  return &_Texel__type_support;
}

#if defined(__cplusplus)
}
#endif
