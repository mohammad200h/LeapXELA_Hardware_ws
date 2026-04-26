// generated from rosidl_typesupport_cpp/resource/idl__type_support.cpp.em
// with input from leap_hand:srv/LeapVelocity.idl
// generated code does not contain a copyright notice

#include "cstddef"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "leap_hand/srv/detail/leap_velocity__struct.hpp"
#include "rosidl_typesupport_cpp/identifier.hpp"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_c/type_support_map.h"
#include "rosidl_typesupport_cpp/message_type_support_dispatch.hpp"
#include "rosidl_typesupport_cpp/visibility_control.h"
#include "rosidl_typesupport_interface/macros.h"

namespace leap_hand
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _LeapVelocity_Request_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _LeapVelocity_Request_type_support_ids_t;

static const _LeapVelocity_Request_type_support_ids_t _LeapVelocity_Request_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _LeapVelocity_Request_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _LeapVelocity_Request_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _LeapVelocity_Request_type_support_symbol_names_t _LeapVelocity_Request_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, leap_hand, srv, LeapVelocity_Request)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, leap_hand, srv, LeapVelocity_Request)),
  }
};

typedef struct _LeapVelocity_Request_type_support_data_t
{
  void * data[2];
} _LeapVelocity_Request_type_support_data_t;

static _LeapVelocity_Request_type_support_data_t _LeapVelocity_Request_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _LeapVelocity_Request_message_typesupport_map = {
  2,
  "leap_hand",
  &_LeapVelocity_Request_message_typesupport_ids.typesupport_identifier[0],
  &_LeapVelocity_Request_message_typesupport_symbol_names.symbol_name[0],
  &_LeapVelocity_Request_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t LeapVelocity_Request_message_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_LeapVelocity_Request_message_typesupport_map),
  ::rosidl_typesupport_cpp::get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace leap_hand

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<leap_hand::srv::LeapVelocity_Request>()
{
  return &::leap_hand::srv::rosidl_typesupport_cpp::LeapVelocity_Request_message_type_support_handle;
}

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_cpp, leap_hand, srv, LeapVelocity_Request)() {
  return get_message_type_support_handle<leap_hand::srv::LeapVelocity_Request>();
}

#ifdef __cplusplus
}
#endif
}  // namespace rosidl_typesupport_cpp

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "leap_hand/srv/detail/leap_velocity__struct.hpp"
// already included above
// #include "rosidl_typesupport_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support_dispatch.hpp"
// already included above
// #include "rosidl_typesupport_cpp/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace leap_hand
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _LeapVelocity_Response_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _LeapVelocity_Response_type_support_ids_t;

static const _LeapVelocity_Response_type_support_ids_t _LeapVelocity_Response_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _LeapVelocity_Response_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _LeapVelocity_Response_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _LeapVelocity_Response_type_support_symbol_names_t _LeapVelocity_Response_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, leap_hand, srv, LeapVelocity_Response)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, leap_hand, srv, LeapVelocity_Response)),
  }
};

typedef struct _LeapVelocity_Response_type_support_data_t
{
  void * data[2];
} _LeapVelocity_Response_type_support_data_t;

static _LeapVelocity_Response_type_support_data_t _LeapVelocity_Response_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _LeapVelocity_Response_message_typesupport_map = {
  2,
  "leap_hand",
  &_LeapVelocity_Response_message_typesupport_ids.typesupport_identifier[0],
  &_LeapVelocity_Response_message_typesupport_symbol_names.symbol_name[0],
  &_LeapVelocity_Response_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t LeapVelocity_Response_message_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_LeapVelocity_Response_message_typesupport_map),
  ::rosidl_typesupport_cpp::get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace leap_hand

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<leap_hand::srv::LeapVelocity_Response>()
{
  return &::leap_hand::srv::rosidl_typesupport_cpp::LeapVelocity_Response_message_type_support_handle;
}

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_cpp, leap_hand, srv, LeapVelocity_Response)() {
  return get_message_type_support_handle<leap_hand::srv::LeapVelocity_Response>();
}

#ifdef __cplusplus
}
#endif
}  // namespace rosidl_typesupport_cpp

// already included above
// #include "cstddef"
#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "leap_hand/srv/detail/leap_velocity__struct.hpp"
// already included above
// #include "rosidl_typesupport_cpp/identifier.hpp"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
#include "rosidl_typesupport_cpp/service_type_support_dispatch.hpp"
// already included above
// #include "rosidl_typesupport_cpp/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace leap_hand
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _LeapVelocity_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _LeapVelocity_type_support_ids_t;

static const _LeapVelocity_type_support_ids_t _LeapVelocity_service_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _LeapVelocity_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _LeapVelocity_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _LeapVelocity_type_support_symbol_names_t _LeapVelocity_service_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, leap_hand, srv, LeapVelocity)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, leap_hand, srv, LeapVelocity)),
  }
};

typedef struct _LeapVelocity_type_support_data_t
{
  void * data[2];
} _LeapVelocity_type_support_data_t;

static _LeapVelocity_type_support_data_t _LeapVelocity_service_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _LeapVelocity_service_typesupport_map = {
  2,
  "leap_hand",
  &_LeapVelocity_service_typesupport_ids.typesupport_identifier[0],
  &_LeapVelocity_service_typesupport_symbol_names.symbol_name[0],
  &_LeapVelocity_service_typesupport_data.data[0],
};

static const rosidl_service_type_support_t LeapVelocity_service_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_LeapVelocity_service_typesupport_map),
  ::rosidl_typesupport_cpp::get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace leap_hand

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_service_type_support_t *
get_service_type_support_handle<leap_hand::srv::LeapVelocity>()
{
  return &::leap_hand::srv::rosidl_typesupport_cpp::LeapVelocity_service_type_support_handle;
}

}  // namespace rosidl_typesupport_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_cpp, leap_hand, srv, LeapVelocity)() {
  return ::rosidl_typesupport_cpp::get_service_type_support_handle<leap_hand::srv::LeapVelocity>();
}

#ifdef __cplusplus
}
#endif
