// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from arm_server:action/Execute.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_HPP_
#define ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_Goal __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_Goal __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_Goal_
{
  using Type = Execute_Goal_<ContainerAllocator>;

  explicit Execute_Goal_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->plan_id = 0ull;
    }
  }

  explicit Execute_Goal_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->plan_id = 0ull;
    }
  }

  // field types and members
  using _plan_id_type =
    uint64_t;
  _plan_id_type plan_id;

  // setters for named parameter idiom
  Type & set__plan_id(
    const uint64_t & _arg)
  {
    this->plan_id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_Goal_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_Goal_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_Goal_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_Goal_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Goal_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Goal_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Goal_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Goal_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_Goal_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_Goal_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_Goal
    std::shared_ptr<arm_server::action::Execute_Goal_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_Goal
    std::shared_ptr<arm_server::action::Execute_Goal_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_Goal_ & other) const
  {
    if (this->plan_id != other.plan_id) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_Goal_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_Goal_

// alias to use template instance with default allocator
using Execute_Goal =
  arm_server::action::Execute_Goal_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server


#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_Result __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_Result __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_Result_
{
  using Type = Execute_Result_<ContainerAllocator>;

  explicit Execute_Result_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
    }
  }

  explicit Execute_Result_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : message(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
    }
  }

  // field types and members
  using _success_type =
    bool;
  _success_type success;
  using _message_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _message_type message;

  // setters for named parameter idiom
  Type & set__success(
    const bool & _arg)
  {
    this->success = _arg;
    return *this;
  }
  Type & set__message(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->message = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_Result_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_Result_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_Result_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_Result_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Result_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Result_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Result_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Result_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_Result_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_Result_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_Result
    std::shared_ptr<arm_server::action::Execute_Result_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_Result
    std::shared_ptr<arm_server::action::Execute_Result_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_Result_ & other) const
  {
    if (this->success != other.success) {
      return false;
    }
    if (this->message != other.message) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_Result_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_Result_

// alias to use template instance with default allocator
using Execute_Result =
  arm_server::action::Execute_Result_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server


#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_Feedback __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_Feedback __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_Feedback_
{
  using Type = Execute_Feedback_<ContainerAllocator>;

  explicit Execute_Feedback_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0;
    }
  }

  explicit Execute_Feedback_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0;
    }
  }

  // field types and members
  using _progress_type =
    double;
  _progress_type progress;

  // setters for named parameter idiom
  Type & set__progress(
    const double & _arg)
  {
    this->progress = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_Feedback_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_Feedback_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Feedback_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_Feedback_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_Feedback
    std::shared_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_Feedback
    std::shared_ptr<arm_server::action::Execute_Feedback_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_Feedback_ & other) const
  {
    if (this->progress != other.progress) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_Feedback_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_Feedback_

// alias to use template instance with default allocator
using Execute_Feedback =
  arm_server::action::Execute_Feedback_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server


// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'goal'
#include "arm_server/action/detail/execute__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_SendGoal_Request __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_SendGoal_Request __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_SendGoal_Request_
{
  using Type = Execute_SendGoal_Request_<ContainerAllocator>;

  explicit Execute_SendGoal_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    goal(_init)
  {
    (void)_init;
  }

  explicit Execute_SendGoal_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    goal(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _goal_type =
    arm_server::action::Execute_Goal_<ContainerAllocator>;
  _goal_type goal;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__goal(
    const arm_server::action::Execute_Goal_<ContainerAllocator> & _arg)
  {
    this->goal = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_SendGoal_Request
    std::shared_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_SendGoal_Request
    std::shared_ptr<arm_server::action::Execute_SendGoal_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_SendGoal_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->goal != other.goal) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_SendGoal_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_SendGoal_Request_

// alias to use template instance with default allocator
using Execute_SendGoal_Request =
  arm_server::action::Execute_SendGoal_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server


// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_SendGoal_Response __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_SendGoal_Response __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_SendGoal_Response_
{
  using Type = Execute_SendGoal_Response_<ContainerAllocator>;

  explicit Execute_SendGoal_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  explicit Execute_SendGoal_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  // field types and members
  using _accepted_type =
    bool;
  _accepted_type accepted;
  using _stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _stamp_type stamp;

  // setters for named parameter idiom
  Type & set__accepted(
    const bool & _arg)
  {
    this->accepted = _arg;
    return *this;
  }
  Type & set__stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->stamp = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_SendGoal_Response
    std::shared_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_SendGoal_Response
    std::shared_ptr<arm_server::action::Execute_SendGoal_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_SendGoal_Response_ & other) const
  {
    if (this->accepted != other.accepted) {
      return false;
    }
    if (this->stamp != other.stamp) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_SendGoal_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_SendGoal_Response_

// alias to use template instance with default allocator
using Execute_SendGoal_Response =
  arm_server::action::Execute_SendGoal_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server

namespace arm_server
{

namespace action
{

struct Execute_SendGoal
{
  using Request = arm_server::action::Execute_SendGoal_Request;
  using Response = arm_server::action::Execute_SendGoal_Response;
};

}  // namespace action

}  // namespace arm_server


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_GetResult_Request __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_GetResult_Request __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_GetResult_Request_
{
  using Type = Execute_GetResult_Request_<ContainerAllocator>;

  explicit Execute_GetResult_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init)
  {
    (void)_init;
  }

  explicit Execute_GetResult_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_GetResult_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_GetResult_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_GetResult_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_GetResult_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_GetResult_Request
    std::shared_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_GetResult_Request
    std::shared_ptr<arm_server::action::Execute_GetResult_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_GetResult_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_GetResult_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_GetResult_Request_

// alias to use template instance with default allocator
using Execute_GetResult_Request =
  arm_server::action::Execute_GetResult_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server


// Include directives for member types
// Member 'result'
// already included above
// #include "arm_server/action/detail/execute__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_GetResult_Response __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_GetResult_Response __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_GetResult_Response_
{
  using Type = Execute_GetResult_Response_<ContainerAllocator>;

  explicit Execute_GetResult_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  explicit Execute_GetResult_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  // field types and members
  using _status_type =
    int8_t;
  _status_type status;
  using _result_type =
    arm_server::action::Execute_Result_<ContainerAllocator>;
  _result_type result;

  // setters for named parameter idiom
  Type & set__status(
    const int8_t & _arg)
  {
    this->status = _arg;
    return *this;
  }
  Type & set__result(
    const arm_server::action::Execute_Result_<ContainerAllocator> & _arg)
  {
    this->result = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_GetResult_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_GetResult_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_GetResult_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_GetResult_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_GetResult_Response
    std::shared_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_GetResult_Response
    std::shared_ptr<arm_server::action::Execute_GetResult_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_GetResult_Response_ & other) const
  {
    if (this->status != other.status) {
      return false;
    }
    if (this->result != other.result) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_GetResult_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_GetResult_Response_

// alias to use template instance with default allocator
using Execute_GetResult_Response =
  arm_server::action::Execute_GetResult_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server

namespace arm_server
{

namespace action
{

struct Execute_GetResult
{
  using Request = arm_server::action::Execute_GetResult_Request;
  using Response = arm_server::action::Execute_GetResult_Response;
};

}  // namespace action

}  // namespace arm_server


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'feedback'
// already included above
// #include "arm_server/action/detail/execute__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__arm_server__action__Execute_FeedbackMessage __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__action__Execute_FeedbackMessage __declspec(deprecated)
#endif

namespace arm_server
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct Execute_FeedbackMessage_
{
  using Type = Execute_FeedbackMessage_<ContainerAllocator>;

  explicit Execute_FeedbackMessage_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    feedback(_init)
  {
    (void)_init;
  }

  explicit Execute_FeedbackMessage_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    feedback(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _feedback_type =
    arm_server::action::Execute_Feedback_<ContainerAllocator>;
  _feedback_type feedback;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__feedback(
    const arm_server::action::Execute_Feedback_<ContainerAllocator> & _arg)
  {
    this->feedback = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__action__Execute_FeedbackMessage
    std::shared_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__action__Execute_FeedbackMessage
    std::shared_ptr<arm_server::action::Execute_FeedbackMessage_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Execute_FeedbackMessage_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->feedback != other.feedback) {
      return false;
    }
    return true;
  }
  bool operator!=(const Execute_FeedbackMessage_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Execute_FeedbackMessage_

// alias to use template instance with default allocator
using Execute_FeedbackMessage =
  arm_server::action::Execute_FeedbackMessage_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace arm_server

#include "action_msgs/srv/cancel_goal.hpp"
#include "action_msgs/msg/goal_info.hpp"
#include "action_msgs/msg/goal_status_array.hpp"

namespace arm_server
{

namespace action
{

struct Execute
{
  /// The goal message defined in the action definition.
  using Goal = arm_server::action::Execute_Goal;
  /// The result message defined in the action definition.
  using Result = arm_server::action::Execute_Result;
  /// The feedback message defined in the action definition.
  using Feedback = arm_server::action::Execute_Feedback;

  struct Impl
  {
    /// The send_goal service using a wrapped version of the goal message as a request.
    using SendGoalService = arm_server::action::Execute_SendGoal;
    /// The get_result service using a wrapped version of the result message as a response.
    using GetResultService = arm_server::action::Execute_GetResult;
    /// The feedback message with generic fields which wraps the feedback message.
    using FeedbackMessage = arm_server::action::Execute_FeedbackMessage;

    /// The generic service to cancel a goal.
    using CancelGoalService = action_msgs::srv::CancelGoal;
    /// The generic message for the status of a goal.
    using GoalStatusMessage = action_msgs::msg::GoalStatusArray;
  };
};

typedef struct Execute Execute;

}  // namespace action

}  // namespace arm_server

#endif  // ARM_SERVER__ACTION__DETAIL__EXECUTE__STRUCT_HPP_
