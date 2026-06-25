// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from arm_server:action/Execute.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__ACTION__DETAIL__EXECUTE__BUILDER_HPP_
#define ARM_SERVER__ACTION__DETAIL__EXECUTE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "arm_server/action/detail/execute__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_Goal_plan_id
{
public:
  Init_Execute_Goal_plan_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::arm_server::action::Execute_Goal plan_id(::arm_server::action::Execute_Goal::_plan_id_type arg)
  {
    msg_.plan_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_Goal msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_Goal>()
{
  return arm_server::action::builder::Init_Execute_Goal_plan_id();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_Result_message
{
public:
  explicit Init_Execute_Result_message(::arm_server::action::Execute_Result & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Execute_Result message(::arm_server::action::Execute_Result::_message_type arg)
  {
    msg_.message = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_Result msg_;
};

class Init_Execute_Result_success
{
public:
  Init_Execute_Result_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Execute_Result_message success(::arm_server::action::Execute_Result::_success_type arg)
  {
    msg_.success = std::move(arg);
    return Init_Execute_Result_message(msg_);
  }

private:
  ::arm_server::action::Execute_Result msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_Result>()
{
  return arm_server::action::builder::Init_Execute_Result_success();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_Feedback_progress
{
public:
  Init_Execute_Feedback_progress()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::arm_server::action::Execute_Feedback progress(::arm_server::action::Execute_Feedback::_progress_type arg)
  {
    msg_.progress = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_Feedback msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_Feedback>()
{
  return arm_server::action::builder::Init_Execute_Feedback_progress();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_SendGoal_Request_goal
{
public:
  explicit Init_Execute_SendGoal_Request_goal(::arm_server::action::Execute_SendGoal_Request & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Execute_SendGoal_Request goal(::arm_server::action::Execute_SendGoal_Request::_goal_type arg)
  {
    msg_.goal = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_SendGoal_Request msg_;
};

class Init_Execute_SendGoal_Request_goal_id
{
public:
  Init_Execute_SendGoal_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Execute_SendGoal_Request_goal goal_id(::arm_server::action::Execute_SendGoal_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_Execute_SendGoal_Request_goal(msg_);
  }

private:
  ::arm_server::action::Execute_SendGoal_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_SendGoal_Request>()
{
  return arm_server::action::builder::Init_Execute_SendGoal_Request_goal_id();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_SendGoal_Response_stamp
{
public:
  explicit Init_Execute_SendGoal_Response_stamp(::arm_server::action::Execute_SendGoal_Response & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Execute_SendGoal_Response stamp(::arm_server::action::Execute_SendGoal_Response::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_SendGoal_Response msg_;
};

class Init_Execute_SendGoal_Response_accepted
{
public:
  Init_Execute_SendGoal_Response_accepted()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Execute_SendGoal_Response_stamp accepted(::arm_server::action::Execute_SendGoal_Response::_accepted_type arg)
  {
    msg_.accepted = std::move(arg);
    return Init_Execute_SendGoal_Response_stamp(msg_);
  }

private:
  ::arm_server::action::Execute_SendGoal_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_SendGoal_Response>()
{
  return arm_server::action::builder::Init_Execute_SendGoal_Response_accepted();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_GetResult_Request_goal_id
{
public:
  Init_Execute_GetResult_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::arm_server::action::Execute_GetResult_Request goal_id(::arm_server::action::Execute_GetResult_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_GetResult_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_GetResult_Request>()
{
  return arm_server::action::builder::Init_Execute_GetResult_Request_goal_id();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_GetResult_Response_result
{
public:
  explicit Init_Execute_GetResult_Response_result(::arm_server::action::Execute_GetResult_Response & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Execute_GetResult_Response result(::arm_server::action::Execute_GetResult_Response::_result_type arg)
  {
    msg_.result = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_GetResult_Response msg_;
};

class Init_Execute_GetResult_Response_status
{
public:
  Init_Execute_GetResult_Response_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Execute_GetResult_Response_result status(::arm_server::action::Execute_GetResult_Response::_status_type arg)
  {
    msg_.status = std::move(arg);
    return Init_Execute_GetResult_Response_result(msg_);
  }

private:
  ::arm_server::action::Execute_GetResult_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_GetResult_Response>()
{
  return arm_server::action::builder::Init_Execute_GetResult_Response_status();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Execute_FeedbackMessage_feedback
{
public:
  explicit Init_Execute_FeedbackMessage_feedback(::arm_server::action::Execute_FeedbackMessage & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Execute_FeedbackMessage feedback(::arm_server::action::Execute_FeedbackMessage::_feedback_type arg)
  {
    msg_.feedback = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Execute_FeedbackMessage msg_;
};

class Init_Execute_FeedbackMessage_goal_id
{
public:
  Init_Execute_FeedbackMessage_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Execute_FeedbackMessage_feedback goal_id(::arm_server::action::Execute_FeedbackMessage::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_Execute_FeedbackMessage_feedback(msg_);
  }

private:
  ::arm_server::action::Execute_FeedbackMessage msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Execute_FeedbackMessage>()
{
  return arm_server::action::builder::Init_Execute_FeedbackMessage_goal_id();
}

}  // namespace arm_server

#endif  // ARM_SERVER__ACTION__DETAIL__EXECUTE__BUILDER_HPP_
