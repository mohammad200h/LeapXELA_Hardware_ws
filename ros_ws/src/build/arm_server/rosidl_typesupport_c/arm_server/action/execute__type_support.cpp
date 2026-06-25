// generated from rosidl_typesupport_c/resource/idl__type_support.cpp.em
// with input from arm_server:action/Execute.idl
// generated code does not contain a copyright notice

#include "cstddef"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "arm_server/action/detail/execute__struct.h"
#include "arm_server/action/detail/execute__type_support.h"
#include "rosidl_typesupport_c/identifier.h"
#include "rosidl_typesupport_c/message_type_support_dispatch.h"
#include "rosidl_typesupport_c/type_support_map.h"
#include "rosidl_typesupport_c/visibility_control.h"
#include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_Goal_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_Goal_type_support_ids_t;

static const _Execute_Goal_type_support_ids_t _Execute_Goal_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_Goal_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_Goal_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_Goal_type_support_symbol_names_t _Execute_Goal_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_Goal)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_Goal)),
  }
};

typedef struct _Execute_Goal_type_support_data_t
{
  void * data[2];
} _Execute_Goal_type_support_data_t;

static _Execute_Goal_type_support_data_t _Execute_Goal_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_Goal_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_Goal_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_Goal_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_Goal_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_Goal_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_Goal_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_Goal)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_Goal_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_Result_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_Result_type_support_ids_t;

static const _Execute_Result_type_support_ids_t _Execute_Result_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_Result_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_Result_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_Result_type_support_symbol_names_t _Execute_Result_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_Result)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_Result)),
  }
};

typedef struct _Execute_Result_type_support_data_t
{
  void * data[2];
} _Execute_Result_type_support_data_t;

static _Execute_Result_type_support_data_t _Execute_Result_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_Result_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_Result_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_Result_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_Result_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_Result_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_Result_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_Result)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_Result_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_Feedback_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_Feedback_type_support_ids_t;

static const _Execute_Feedback_type_support_ids_t _Execute_Feedback_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_Feedback_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_Feedback_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_Feedback_type_support_symbol_names_t _Execute_Feedback_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_Feedback)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_Feedback)),
  }
};

typedef struct _Execute_Feedback_type_support_data_t
{
  void * data[2];
} _Execute_Feedback_type_support_data_t;

static _Execute_Feedback_type_support_data_t _Execute_Feedback_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_Feedback_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_Feedback_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_Feedback_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_Feedback_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_Feedback_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_Feedback_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_Feedback)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_Feedback_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_SendGoal_Request_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_SendGoal_Request_type_support_ids_t;

static const _Execute_SendGoal_Request_type_support_ids_t _Execute_SendGoal_Request_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_SendGoal_Request_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_SendGoal_Request_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_SendGoal_Request_type_support_symbol_names_t _Execute_SendGoal_Request_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_SendGoal_Request)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_SendGoal_Request)),
  }
};

typedef struct _Execute_SendGoal_Request_type_support_data_t
{
  void * data[2];
} _Execute_SendGoal_Request_type_support_data_t;

static _Execute_SendGoal_Request_type_support_data_t _Execute_SendGoal_Request_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_SendGoal_Request_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_SendGoal_Request_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_SendGoal_Request_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_SendGoal_Request_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_SendGoal_Request_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_SendGoal_Request_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_SendGoal_Request)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_SendGoal_Request_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_SendGoal_Response_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_SendGoal_Response_type_support_ids_t;

static const _Execute_SendGoal_Response_type_support_ids_t _Execute_SendGoal_Response_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_SendGoal_Response_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_SendGoal_Response_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_SendGoal_Response_type_support_symbol_names_t _Execute_SendGoal_Response_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_SendGoal_Response)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_SendGoal_Response)),
  }
};

typedef struct _Execute_SendGoal_Response_type_support_data_t
{
  void * data[2];
} _Execute_SendGoal_Response_type_support_data_t;

static _Execute_SendGoal_Response_type_support_data_t _Execute_SendGoal_Response_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_SendGoal_Response_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_SendGoal_Response_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_SendGoal_Response_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_SendGoal_Response_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_SendGoal_Response_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_SendGoal_Response_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_SendGoal_Response)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_SendGoal_Response_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
#include "rosidl_typesupport_c/service_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_SendGoal_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_SendGoal_type_support_ids_t;

static const _Execute_SendGoal_type_support_ids_t _Execute_SendGoal_service_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_SendGoal_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_SendGoal_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_SendGoal_type_support_symbol_names_t _Execute_SendGoal_service_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_SendGoal)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_SendGoal)),
  }
};

typedef struct _Execute_SendGoal_type_support_data_t
{
  void * data[2];
} _Execute_SendGoal_type_support_data_t;

static _Execute_SendGoal_type_support_data_t _Execute_SendGoal_service_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_SendGoal_service_typesupport_map = {
  2,
  "arm_server",
  &_Execute_SendGoal_service_typesupport_ids.typesupport_identifier[0],
  &_Execute_SendGoal_service_typesupport_symbol_names.symbol_name[0],
  &_Execute_SendGoal_service_typesupport_data.data[0],
};

static const rosidl_service_type_support_t Execute_SendGoal_service_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_SendGoal_service_typesupport_map),
  rosidl_typesupport_c__get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_SendGoal)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_SendGoal_service_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_GetResult_Request_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_GetResult_Request_type_support_ids_t;

static const _Execute_GetResult_Request_type_support_ids_t _Execute_GetResult_Request_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_GetResult_Request_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_GetResult_Request_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_GetResult_Request_type_support_symbol_names_t _Execute_GetResult_Request_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_GetResult_Request)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_GetResult_Request)),
  }
};

typedef struct _Execute_GetResult_Request_type_support_data_t
{
  void * data[2];
} _Execute_GetResult_Request_type_support_data_t;

static _Execute_GetResult_Request_type_support_data_t _Execute_GetResult_Request_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_GetResult_Request_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_GetResult_Request_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_GetResult_Request_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_GetResult_Request_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_GetResult_Request_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_GetResult_Request_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_GetResult_Request)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_GetResult_Request_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_GetResult_Response_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_GetResult_Response_type_support_ids_t;

static const _Execute_GetResult_Response_type_support_ids_t _Execute_GetResult_Response_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_GetResult_Response_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_GetResult_Response_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_GetResult_Response_type_support_symbol_names_t _Execute_GetResult_Response_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_GetResult_Response)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_GetResult_Response)),
  }
};

typedef struct _Execute_GetResult_Response_type_support_data_t
{
  void * data[2];
} _Execute_GetResult_Response_type_support_data_t;

static _Execute_GetResult_Response_type_support_data_t _Execute_GetResult_Response_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_GetResult_Response_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_GetResult_Response_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_GetResult_Response_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_GetResult_Response_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_GetResult_Response_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_GetResult_Response_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_GetResult_Response)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_GetResult_Response_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/service_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_GetResult_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_GetResult_type_support_ids_t;

static const _Execute_GetResult_type_support_ids_t _Execute_GetResult_service_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_GetResult_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_GetResult_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_GetResult_type_support_symbol_names_t _Execute_GetResult_service_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_GetResult)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_GetResult)),
  }
};

typedef struct _Execute_GetResult_type_support_data_t
{
  void * data[2];
} _Execute_GetResult_type_support_data_t;

static _Execute_GetResult_type_support_data_t _Execute_GetResult_service_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_GetResult_service_typesupport_map = {
  2,
  "arm_server",
  &_Execute_GetResult_service_typesupport_ids.typesupport_identifier[0],
  &_Execute_GetResult_service_typesupport_symbol_names.symbol_name[0],
  &_Execute_GetResult_service_typesupport_data.data[0],
};

static const rosidl_service_type_support_t Execute_GetResult_service_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_GetResult_service_typesupport_map),
  rosidl_typesupport_c__get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_GetResult)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_GetResult_service_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "arm_server/action/detail/execute__struct.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"
// already included above
// #include "rosidl_typesupport_c/identifier.h"
// already included above
// #include "rosidl_typesupport_c/message_type_support_dispatch.h"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_c/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_c
{

typedef struct _Execute_FeedbackMessage_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _Execute_FeedbackMessage_type_support_ids_t;

static const _Execute_FeedbackMessage_type_support_ids_t _Execute_FeedbackMessage_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_c",  // ::rosidl_typesupport_fastrtps_c::typesupport_identifier,
    "rosidl_typesupport_introspection_c",  // ::rosidl_typesupport_introspection_c::typesupport_identifier,
  }
};

typedef struct _Execute_FeedbackMessage_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _Execute_FeedbackMessage_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _Execute_FeedbackMessage_type_support_symbol_names_t _Execute_FeedbackMessage_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, arm_server, action, Execute_FeedbackMessage)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, arm_server, action, Execute_FeedbackMessage)),
  }
};

typedef struct _Execute_FeedbackMessage_type_support_data_t
{
  void * data[2];
} _Execute_FeedbackMessage_type_support_data_t;

static _Execute_FeedbackMessage_type_support_data_t _Execute_FeedbackMessage_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _Execute_FeedbackMessage_message_typesupport_map = {
  2,
  "arm_server",
  &_Execute_FeedbackMessage_message_typesupport_ids.typesupport_identifier[0],
  &_Execute_FeedbackMessage_message_typesupport_symbol_names.symbol_name[0],
  &_Execute_FeedbackMessage_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t Execute_FeedbackMessage_message_type_support_handle = {
  rosidl_typesupport_c__typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_Execute_FeedbackMessage_message_typesupport_map),
  rosidl_typesupport_c__get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_c

}  // namespace action

}  // namespace arm_server

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_c, arm_server, action, Execute_FeedbackMessage)() {
  return &::arm_server::action::rosidl_typesupport_c::Execute_FeedbackMessage_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

#include "action_msgs/msg/goal_status_array.h"
#include "action_msgs/srv/cancel_goal.h"
#include "arm_server/action/execute.h"
// already included above
// #include "arm_server/action/detail/execute__type_support.h"

static rosidl_action_type_support_t _arm_server__action__Execute__typesupport_c;

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_action_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__ACTION_SYMBOL_NAME(
  rosidl_typesupport_c, arm_server, action, Execute)()
{
  // Thread-safe by always writing the same values to the static struct
  _arm_server__action__Execute__typesupport_c.goal_service_type_support =
    ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(
    rosidl_typesupport_c, arm_server, action, Execute_SendGoal)();
  _arm_server__action__Execute__typesupport_c.result_service_type_support =
    ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(
    rosidl_typesupport_c, arm_server, action, Execute_GetResult)();
  _arm_server__action__Execute__typesupport_c.cancel_service_type_support =
    ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(
    rosidl_typesupport_c, action_msgs, srv, CancelGoal)();
  _arm_server__action__Execute__typesupport_c.feedback_message_type_support =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(
    rosidl_typesupport_c, arm_server, action, Execute_FeedbackMessage)();
  _arm_server__action__Execute__typesupport_c.status_message_type_support =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(
    rosidl_typesupport_c, action_msgs, msg, GoalStatusArray)();

  return &_arm_server__action__Execute__typesupport_c;
}

#ifdef __cplusplus
}
#endif
