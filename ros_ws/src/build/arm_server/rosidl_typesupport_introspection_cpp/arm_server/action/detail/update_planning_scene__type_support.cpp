// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from arm_server:action/UpdatePlanningScene.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "arm_server/action/detail/update_planning_scene__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_Goal_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_Goal(_init);
}

void UpdatePlanningScene_Goal_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_Goal *>(message_memory);
  typed_message->~UpdatePlanningScene_Goal();
}

size_t size_function__UpdatePlanningScene_Goal__objects(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<arm_server::msg::SceneObject> *>(untyped_member);
  return member->size();
}

const void * get_const_function__UpdatePlanningScene_Goal__objects(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<arm_server::msg::SceneObject> *>(untyped_member);
  return &member[index];
}

void * get_function__UpdatePlanningScene_Goal__objects(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<arm_server::msg::SceneObject> *>(untyped_member);
  return &member[index];
}

void fetch_function__UpdatePlanningScene_Goal__objects(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const arm_server::msg::SceneObject *>(
    get_const_function__UpdatePlanningScene_Goal__objects(untyped_member, index));
  auto & value = *reinterpret_cast<arm_server::msg::SceneObject *>(untyped_value);
  value = item;
}

void assign_function__UpdatePlanningScene_Goal__objects(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<arm_server::msg::SceneObject *>(
    get_function__UpdatePlanningScene_Goal__objects(untyped_member, index));
  const auto & value = *reinterpret_cast<const arm_server::msg::SceneObject *>(untyped_value);
  item = value;
}

void resize_function__UpdatePlanningScene_Goal__objects(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<arm_server::msg::SceneObject> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_Goal_message_member_array[2] = {
  {
    "objects",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<arm_server::msg::SceneObject>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Goal, objects),  // bytes offset in struct
    nullptr,  // default value
    size_function__UpdatePlanningScene_Goal__objects,  // size() function pointer
    get_const_function__UpdatePlanningScene_Goal__objects,  // get_const(index) function pointer
    get_function__UpdatePlanningScene_Goal__objects,  // get(index) function pointer
    fetch_function__UpdatePlanningScene_Goal__objects,  // fetch(index, &value) function pointer
    assign_function__UpdatePlanningScene_Goal__objects,  // assign(index, value) function pointer
    resize_function__UpdatePlanningScene_Goal__objects  // resize(index) function pointer
  },
  {
    "clear_existing",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Goal, clear_existing),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_Goal_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_Goal",  // message name
  2,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_Goal),
  UpdatePlanningScene_Goal_message_member_array,  // message members
  UpdatePlanningScene_Goal_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_Goal_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_Goal_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_Goal_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Goal>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Goal_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_Goal)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Goal_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_Result_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_Result(_init);
}

void UpdatePlanningScene_Result_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_Result *>(message_memory);
  typed_message->~UpdatePlanningScene_Result();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_Result_message_member_array[3] = {
  {
    "success",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Result, success),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "message",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Result, message),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "objects_added",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_UINT32,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Result, objects_added),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_Result_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_Result",  // message name
  3,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_Result),
  UpdatePlanningScene_Result_message_member_array,  // message members
  UpdatePlanningScene_Result_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_Result_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_Result_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_Result_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Result>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Result_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_Result)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Result_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_Feedback_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_Feedback(_init);
}

void UpdatePlanningScene_Feedback_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_Feedback *>(message_memory);
  typed_message->~UpdatePlanningScene_Feedback();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_Feedback_message_member_array[1] = {
  {
    "progress",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_Feedback, progress),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_Feedback_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_Feedback",  // message name
  1,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_Feedback),
  UpdatePlanningScene_Feedback_message_member_array,  // message members
  UpdatePlanningScene_Feedback_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_Feedback_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_Feedback_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_Feedback_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Feedback>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Feedback_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_Feedback)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_Feedback_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_SendGoal_Request_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_SendGoal_Request(_init);
}

void UpdatePlanningScene_SendGoal_Request_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_SendGoal_Request *>(message_memory);
  typed_message->~UpdatePlanningScene_SendGoal_Request();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_SendGoal_Request_message_member_array[2] = {
  {
    "goal_id",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<unique_identifier_msgs::msg::UUID>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_SendGoal_Request, goal_id),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "goal",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Goal>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_SendGoal_Request, goal),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_SendGoal_Request_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_SendGoal_Request",  // message name
  2,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_SendGoal_Request),
  UpdatePlanningScene_SendGoal_Request_message_member_array,  // message members
  UpdatePlanningScene_SendGoal_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_SendGoal_Request_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_SendGoal_Request_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_SendGoal_Request_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_SendGoal_Request>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_SendGoal_Request_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_SendGoal_Request)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_SendGoal_Request_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_SendGoal_Response_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_SendGoal_Response(_init);
}

void UpdatePlanningScene_SendGoal_Response_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_SendGoal_Response *>(message_memory);
  typed_message->~UpdatePlanningScene_SendGoal_Response();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_SendGoal_Response_message_member_array[2] = {
  {
    "accepted",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_SendGoal_Response, accepted),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "stamp",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<builtin_interfaces::msg::Time>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_SendGoal_Response, stamp),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_SendGoal_Response_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_SendGoal_Response",  // message name
  2,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_SendGoal_Response),
  UpdatePlanningScene_SendGoal_Response_message_member_array,  // message members
  UpdatePlanningScene_SendGoal_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_SendGoal_Response_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_SendGoal_Response_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_SendGoal_Response_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_SendGoal_Response>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_SendGoal_Response_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_SendGoal_Response)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_SendGoal_Response_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/service_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/service_type_support_decl.hpp"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

// this is intentionally not const to allow initialization later to prevent an initialization race
static ::rosidl_typesupport_introspection_cpp::ServiceMembers UpdatePlanningScene_SendGoal_service_members = {
  "arm_server::action",  // service namespace
  "UpdatePlanningScene_SendGoal",  // service name
  // these two fields are initialized below on the first access
  // see get_service_type_support_handle<arm_server::action::UpdatePlanningScene_SendGoal>()
  nullptr,  // request message
  nullptr  // response message
};

static const rosidl_service_type_support_t UpdatePlanningScene_SendGoal_service_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_SendGoal_service_members,
  get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
get_service_type_support_handle<arm_server::action::UpdatePlanningScene_SendGoal>()
{
  // get a handle to the value to be returned
  auto service_type_support =
    &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_SendGoal_service_type_support_handle;
  // get a non-const and properly typed version of the data void *
  auto service_members = const_cast<::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
    static_cast<const ::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
      service_type_support->data));
  // make sure that both the request_members_ and the response_members_ are initialized
  // if they are not, initialize them
  if (
    service_members->request_members_ == nullptr ||
    service_members->response_members_ == nullptr)
  {
    // initialize the request_members_ with the static function from the external library
    service_members->request_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::arm_server::action::UpdatePlanningScene_SendGoal_Request
      >()->data
      );
    // initialize the response_members_ with the static function from the external library
    service_members->response_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::arm_server::action::UpdatePlanningScene_SendGoal_Response
      >()->data
      );
  }
  // finally return the properly initialized service_type_support handle
  return service_type_support;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_SendGoal)() {
  return ::rosidl_typesupport_introspection_cpp::get_service_type_support_handle<arm_server::action::UpdatePlanningScene_SendGoal>();
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_GetResult_Request_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_GetResult_Request(_init);
}

void UpdatePlanningScene_GetResult_Request_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_GetResult_Request *>(message_memory);
  typed_message->~UpdatePlanningScene_GetResult_Request();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_GetResult_Request_message_member_array[1] = {
  {
    "goal_id",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<unique_identifier_msgs::msg::UUID>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_GetResult_Request, goal_id),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_GetResult_Request_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_GetResult_Request",  // message name
  1,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_GetResult_Request),
  UpdatePlanningScene_GetResult_Request_message_member_array,  // message members
  UpdatePlanningScene_GetResult_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_GetResult_Request_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_GetResult_Request_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_GetResult_Request_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_GetResult_Request>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_GetResult_Request_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_GetResult_Request)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_GetResult_Request_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_GetResult_Response_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_GetResult_Response(_init);
}

void UpdatePlanningScene_GetResult_Response_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_GetResult_Response *>(message_memory);
  typed_message->~UpdatePlanningScene_GetResult_Response();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_GetResult_Response_message_member_array[2] = {
  {
    "status",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_INT8,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_GetResult_Response, status),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "result",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Result>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_GetResult_Response, result),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_GetResult_Response_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_GetResult_Response",  // message name
  2,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_GetResult_Response),
  UpdatePlanningScene_GetResult_Response_message_member_array,  // message members
  UpdatePlanningScene_GetResult_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_GetResult_Response_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_GetResult_Response_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_GetResult_Response_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_GetResult_Response>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_GetResult_Response_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_GetResult_Response)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_GetResult_Response_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/service_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/service_type_support_decl.hpp"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

// this is intentionally not const to allow initialization later to prevent an initialization race
static ::rosidl_typesupport_introspection_cpp::ServiceMembers UpdatePlanningScene_GetResult_service_members = {
  "arm_server::action",  // service namespace
  "UpdatePlanningScene_GetResult",  // service name
  // these two fields are initialized below on the first access
  // see get_service_type_support_handle<arm_server::action::UpdatePlanningScene_GetResult>()
  nullptr,  // request message
  nullptr  // response message
};

static const rosidl_service_type_support_t UpdatePlanningScene_GetResult_service_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_GetResult_service_members,
  get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
get_service_type_support_handle<arm_server::action::UpdatePlanningScene_GetResult>()
{
  // get a handle to the value to be returned
  auto service_type_support =
    &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_GetResult_service_type_support_handle;
  // get a non-const and properly typed version of the data void *
  auto service_members = const_cast<::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
    static_cast<const ::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
      service_type_support->data));
  // make sure that both the request_members_ and the response_members_ are initialized
  // if they are not, initialize them
  if (
    service_members->request_members_ == nullptr ||
    service_members->response_members_ == nullptr)
  {
    // initialize the request_members_ with the static function from the external library
    service_members->request_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::arm_server::action::UpdatePlanningScene_GetResult_Request
      >()->data
      );
    // initialize the response_members_ with the static function from the external library
    service_members->response_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::arm_server::action::UpdatePlanningScene_GetResult_Response
      >()->data
      );
  }
  // finally return the properly initialized service_type_support handle
  return service_type_support;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_GetResult)() {
  return ::rosidl_typesupport_introspection_cpp::get_service_type_support_handle<arm_server::action::UpdatePlanningScene_GetResult>();
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "arm_server/action/detail/update_planning_scene__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace arm_server
{

namespace action
{

namespace rosidl_typesupport_introspection_cpp
{

void UpdatePlanningScene_FeedbackMessage_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) arm_server::action::UpdatePlanningScene_FeedbackMessage(_init);
}

void UpdatePlanningScene_FeedbackMessage_fini_function(void * message_memory)
{
  auto typed_message = static_cast<arm_server::action::UpdatePlanningScene_FeedbackMessage *>(message_memory);
  typed_message->~UpdatePlanningScene_FeedbackMessage();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember UpdatePlanningScene_FeedbackMessage_message_member_array[2] = {
  {
    "goal_id",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<unique_identifier_msgs::msg::UUID>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_FeedbackMessage, goal_id),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "feedback",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<arm_server::action::UpdatePlanningScene_Feedback>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(arm_server::action::UpdatePlanningScene_FeedbackMessage, feedback),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers UpdatePlanningScene_FeedbackMessage_message_members = {
  "arm_server::action",  // message namespace
  "UpdatePlanningScene_FeedbackMessage",  // message name
  2,  // number of fields
  sizeof(arm_server::action::UpdatePlanningScene_FeedbackMessage),
  UpdatePlanningScene_FeedbackMessage_message_member_array,  // message members
  UpdatePlanningScene_FeedbackMessage_init_function,  // function to initialize message memory (memory has to be allocated)
  UpdatePlanningScene_FeedbackMessage_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t UpdatePlanningScene_FeedbackMessage_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &UpdatePlanningScene_FeedbackMessage_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace action

}  // namespace arm_server


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<arm_server::action::UpdatePlanningScene_FeedbackMessage>()
{
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_FeedbackMessage_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, arm_server, action, UpdatePlanningScene_FeedbackMessage)() {
  return &::arm_server::action::rosidl_typesupport_introspection_cpp::UpdatePlanningScene_FeedbackMessage_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
