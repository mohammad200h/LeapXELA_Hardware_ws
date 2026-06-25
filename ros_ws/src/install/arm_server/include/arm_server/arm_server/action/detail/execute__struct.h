// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from arm_server:action/Execute.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_H_
#define ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_Goal
{
  uint64_t plan_id;
} arm_server__action__Execute_Goal;

// Struct for a sequence of arm_server__action__Execute_Goal.
typedef struct arm_server__action__Execute_Goal__Sequence
{
  arm_server__action__Execute_Goal * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_Goal__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'message'
#include "rosidl_runtime_c/string.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_Result
{
  bool success;
  rosidl_runtime_c__String message;
} arm_server__action__Execute_Result;

// Struct for a sequence of arm_server__action__Execute_Result.
typedef struct arm_server__action__Execute_Result__Sequence
{
  arm_server__action__Execute_Result * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_Result__Sequence;


// Constants defined in the message

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_Feedback
{
  double progress;
} arm_server__action__Execute_Feedback;

// Struct for a sequence of arm_server__action__Execute_Feedback.
typedef struct arm_server__action__Execute_Feedback__Sequence
{
  arm_server__action__Execute_Feedback * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_Feedback__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'goal'
#include "arm_server/action/detail/execute__struct.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_SendGoal_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
  arm_server__action__Execute_Goal goal;
} arm_server__action__Execute_SendGoal_Request;

// Struct for a sequence of arm_server__action__Execute_SendGoal_Request.
typedef struct arm_server__action__Execute_SendGoal_Request__Sequence
{
  arm_server__action__Execute_SendGoal_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_SendGoal_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_SendGoal_Response
{
  bool accepted;
  builtin_interfaces__msg__Time stamp;
} arm_server__action__Execute_SendGoal_Response;

// Struct for a sequence of arm_server__action__Execute_SendGoal_Response.
typedef struct arm_server__action__Execute_SendGoal_Response__Sequence
{
  arm_server__action__Execute_SendGoal_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_SendGoal_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_GetResult_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
} arm_server__action__Execute_GetResult_Request;

// Struct for a sequence of arm_server__action__Execute_GetResult_Request.
typedef struct arm_server__action__Execute_GetResult_Request__Sequence
{
  arm_server__action__Execute_GetResult_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_GetResult_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'result'
// already included above
// #include "arm_server/action/detail/execute__struct.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_GetResult_Response
{
  int8_t status;
  arm_server__action__Execute_Result result;
} arm_server__action__Execute_GetResult_Response;

// Struct for a sequence of arm_server__action__Execute_GetResult_Response.
typedef struct arm_server__action__Execute_GetResult_Response__Sequence
{
  arm_server__action__Execute_GetResult_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_GetResult_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'feedback'
// already included above
// #include "arm_server/action/detail/execute__struct.h"

/// Struct defined in action/Execute in the package arm_server.
typedef struct arm_server__action__Execute_FeedbackMessage
{
  unique_identifier_msgs__msg__UUID goal_id;
  arm_server__action__Execute_Feedback feedback;
} arm_server__action__Execute_FeedbackMessage;

// Struct for a sequence of arm_server__action__Execute_FeedbackMessage.
typedef struct arm_server__action__Execute_FeedbackMessage__Sequence
{
  arm_server__action__Execute_FeedbackMessage * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} arm_server__action__Execute_FeedbackMessage__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_H_
