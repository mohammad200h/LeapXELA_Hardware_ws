// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_HPP_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'texels'
#include "xela_point_cloud_representation/msg/detail/texel__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__xela_point_cloud_representation__msg__HandSensors __attribute__((deprecated))
#else
# define DEPRECATED__xela_point_cloud_representation__msg__HandSensors __declspec(deprecated)
#endif

namespace xela_point_cloud_representation
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct HandSensors_
{
  using Type = HandSensors_<ContainerAllocator>;

  explicit HandSensors_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_init;
  }

  explicit HandSensors_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_init;
    (void)_alloc;
  }

  // field types and members
  using _texels_type =
    std::vector<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>>;
  _texels_type texels;

  // setters for named parameter idiom
  Type & set__texels(
    const std::vector<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>> & _arg)
  {
    this->texels = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> *;
  using ConstRawPtr =
    const xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__xela_point_cloud_representation__msg__HandSensors
    std::shared_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__xela_point_cloud_representation__msg__HandSensors
    std::shared_ptr<xela_point_cloud_representation::msg::HandSensors_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const HandSensors_ & other) const
  {
    if (this->texels != other.texels) {
      return false;
    }
    return true;
  }
  bool operator!=(const HandSensors_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct HandSensors_

// alias to use template instance with default allocator
using HandSensors =
  xela_point_cloud_representation::msg::HandSensors_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace xela_point_cloud_representation

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__HAND_SENSORS__STRUCT_HPP_
