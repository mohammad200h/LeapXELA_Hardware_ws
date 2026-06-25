// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from arm_server:action/Plan.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__ACTION__DETAIL__PLAN__BUILDER_HPP_
#define ARM_SERVER__ACTION__DETAIL__PLAN__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "arm_server/action/detail/plan__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_Goal_yaw
{
public:
  explicit Init_Plan_Goal_yaw(::arm_server::action::Plan_Goal & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_Goal yaw(::arm_server::action::Plan_Goal::_yaw_type arg)
  {
    msg_.yaw = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

class Init_Plan_Goal_pitch
{
public:
  explicit Init_Plan_Goal_pitch(::arm_server::action::Plan_Goal & msg)
  : msg_(msg)
  {}
  Init_Plan_Goal_yaw pitch(::arm_server::action::Plan_Goal::_pitch_type arg)
  {
    msg_.pitch = std::move(arg);
    return Init_Plan_Goal_yaw(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

class Init_Plan_Goal_roll
{
public:
  explicit Init_Plan_Goal_roll(::arm_server::action::Plan_Goal & msg)
  : msg_(msg)
  {}
  Init_Plan_Goal_pitch roll(::arm_server::action::Plan_Goal::_roll_type arg)
  {
    msg_.roll = std::move(arg);
    return Init_Plan_Goal_pitch(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

class Init_Plan_Goal_z
{
public:
  explicit Init_Plan_Goal_z(::arm_server::action::Plan_Goal & msg)
  : msg_(msg)
  {}
  Init_Plan_Goal_roll z(::arm_server::action::Plan_Goal::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_Plan_Goal_roll(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

class Init_Plan_Goal_y
{
public:
  explicit Init_Plan_Goal_y(::arm_server::action::Plan_Goal & msg)
  : msg_(msg)
  {}
  Init_Plan_Goal_z y(::arm_server::action::Plan_Goal::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_Plan_Goal_z(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

class Init_Plan_Goal_x
{
public:
  Init_Plan_Goal_x()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_Goal_y x(::arm_server::action::Plan_Goal::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_Plan_Goal_y(msg_);
  }

private:
  ::arm_server::action::Plan_Goal msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_Goal>()
{
  return arm_server::action::builder::Init_Plan_Goal_x();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_Result_trajectory_duration
{
public:
  explicit Init_Plan_Result_trajectory_duration(::arm_server::action::Plan_Result & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_Result trajectory_duration(::arm_server::action::Plan_Result::_trajectory_duration_type arg)
  {
    msg_.trajectory_duration = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_Result msg_;
};

class Init_Plan_Result_plan_id
{
public:
  explicit Init_Plan_Result_plan_id(::arm_server::action::Plan_Result & msg)
  : msg_(msg)
  {}
  Init_Plan_Result_trajectory_duration plan_id(::arm_server::action::Plan_Result::_plan_id_type arg)
  {
    msg_.plan_id = std::move(arg);
    return Init_Plan_Result_trajectory_duration(msg_);
  }

private:
  ::arm_server::action::Plan_Result msg_;
};

class Init_Plan_Result_message
{
public:
  explicit Init_Plan_Result_message(::arm_server::action::Plan_Result & msg)
  : msg_(msg)
  {}
  Init_Plan_Result_plan_id message(::arm_server::action::Plan_Result::_message_type arg)
  {
    msg_.message = std::move(arg);
    return Init_Plan_Result_plan_id(msg_);
  }

private:
  ::arm_server::action::Plan_Result msg_;
};

class Init_Plan_Result_success
{
public:
  Init_Plan_Result_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_Result_message success(::arm_server::action::Plan_Result::_success_type arg)
  {
    msg_.success = std::move(arg);
    return Init_Plan_Result_message(msg_);
  }

private:
  ::arm_server::action::Plan_Result msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_Result>()
{
  return arm_server::action::builder::Init_Plan_Result_success();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_Feedback_progress
{
public:
  Init_Plan_Feedback_progress()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::arm_server::action::Plan_Feedback progress(::arm_server::action::Plan_Feedback::_progress_type arg)
  {
    msg_.progress = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_Feedback msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_Feedback>()
{
  return arm_server::action::builder::Init_Plan_Feedback_progress();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_SendGoal_Request_goal
{
public:
  explicit Init_Plan_SendGoal_Request_goal(::arm_server::action::Plan_SendGoal_Request & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_SendGoal_Request goal(::arm_server::action::Plan_SendGoal_Request::_goal_type arg)
  {
    msg_.goal = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_SendGoal_Request msg_;
};

class Init_Plan_SendGoal_Request_goal_id
{
public:
  Init_Plan_SendGoal_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_SendGoal_Request_goal goal_id(::arm_server::action::Plan_SendGoal_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_Plan_SendGoal_Request_goal(msg_);
  }

private:
  ::arm_server::action::Plan_SendGoal_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_SendGoal_Request>()
{
  return arm_server::action::builder::Init_Plan_SendGoal_Request_goal_id();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_SendGoal_Response_stamp
{
public:
  explicit Init_Plan_SendGoal_Response_stamp(::arm_server::action::Plan_SendGoal_Response & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_SendGoal_Response stamp(::arm_server::action::Plan_SendGoal_Response::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_SendGoal_Response msg_;
};

class Init_Plan_SendGoal_Response_accepted
{
public:
  Init_Plan_SendGoal_Response_accepted()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_SendGoal_Response_stamp accepted(::arm_server::action::Plan_SendGoal_Response::_accepted_type arg)
  {
    msg_.accepted = std::move(arg);
    return Init_Plan_SendGoal_Response_stamp(msg_);
  }

private:
  ::arm_server::action::Plan_SendGoal_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_SendGoal_Response>()
{
  return arm_server::action::builder::Init_Plan_SendGoal_Response_accepted();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_GetResult_Request_goal_id
{
public:
  Init_Plan_GetResult_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::arm_server::action::Plan_GetResult_Request goal_id(::arm_server::action::Plan_GetResult_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_GetResult_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_GetResult_Request>()
{
  return arm_server::action::builder::Init_Plan_GetResult_Request_goal_id();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_GetResult_Response_result
{
public:
  explicit Init_Plan_GetResult_Response_result(::arm_server::action::Plan_GetResult_Response & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_GetResult_Response result(::arm_server::action::Plan_GetResult_Response::_result_type arg)
  {
    msg_.result = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_GetResult_Response msg_;
};

class Init_Plan_GetResult_Response_status
{
public:
  Init_Plan_GetResult_Response_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_GetResult_Response_result status(::arm_server::action::Plan_GetResult_Response::_status_type arg)
  {
    msg_.status = std::move(arg);
    return Init_Plan_GetResult_Response_result(msg_);
  }

private:
  ::arm_server::action::Plan_GetResult_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_GetResult_Response>()
{
  return arm_server::action::builder::Init_Plan_GetResult_Response_status();
}

}  // namespace arm_server


namespace arm_server
{

namespace action
{

namespace builder
{

class Init_Plan_FeedbackMessage_feedback
{
public:
  explicit Init_Plan_FeedbackMessage_feedback(::arm_server::action::Plan_FeedbackMessage & msg)
  : msg_(msg)
  {}
  ::arm_server::action::Plan_FeedbackMessage feedback(::arm_server::action::Plan_FeedbackMessage::_feedback_type arg)
  {
    msg_.feedback = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::action::Plan_FeedbackMessage msg_;
};

class Init_Plan_FeedbackMessage_goal_id
{
public:
  Init_Plan_FeedbackMessage_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Plan_FeedbackMessage_feedback goal_id(::arm_server::action::Plan_FeedbackMessage::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_Plan_FeedbackMessage_feedback(msg_);
  }

private:
  ::arm_server::action::Plan_FeedbackMessage msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::action::Plan_FeedbackMessage>()
{
  return arm_server::action::builder::Init_Plan_FeedbackMessage_goal_id();
}

}  // namespace arm_server

#endif  // ARM_SERVER__ACTION__DETAIL__PLAN__BUILDER_HPP_
