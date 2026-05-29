// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_HPP_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__xela_point_cloud_representation__msg__Texel __attribute__((deprecated))
#else
# define DEPRECATED__xela_point_cloud_representation__msg__Texel __declspec(deprecated)
#endif

namespace xela_point_cloud_representation
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct Texel_
{
  using Type = Texel_<ContainerAllocator>;

  explicit Texel_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->taxel_id = 0l;
      this->sensor_name = "";
      this->x = 0.0f;
      this->y = 0.0f;
      this->z = 0.0f;
      this->joint_x = "";
      this->joint_y = "";
      this->joint_z = "";
    }
  }

  explicit Texel_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : sensor_name(_alloc),
    joint_x(_alloc),
    joint_y(_alloc),
    joint_z(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->taxel_id = 0l;
      this->sensor_name = "";
      this->x = 0.0f;
      this->y = 0.0f;
      this->z = 0.0f;
      this->joint_x = "";
      this->joint_y = "";
      this->joint_z = "";
    }
  }

  // field types and members
  using _taxel_id_type =
    int32_t;
  _taxel_id_type taxel_id;
  using _sensor_name_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _sensor_name_type sensor_name;
  using _x_type =
    float;
  _x_type x;
  using _y_type =
    float;
  _y_type y;
  using _z_type =
    float;
  _z_type z;
  using _joint_x_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _joint_x_type joint_x;
  using _joint_y_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _joint_y_type joint_y;
  using _joint_z_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _joint_z_type joint_z;

  // setters for named parameter idiom
  Type & set__taxel_id(
    const int32_t & _arg)
  {
    this->taxel_id = _arg;
    return *this;
  }
  Type & set__sensor_name(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->sensor_name = _arg;
    return *this;
  }
  Type & set__x(
    const float & _arg)
  {
    this->x = _arg;
    return *this;
  }
  Type & set__y(
    const float & _arg)
  {
    this->y = _arg;
    return *this;
  }
  Type & set__z(
    const float & _arg)
  {
    this->z = _arg;
    return *this;
  }
  Type & set__joint_x(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->joint_x = _arg;
    return *this;
  }
  Type & set__joint_y(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->joint_y = _arg;
    return *this;
  }
  Type & set__joint_z(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->joint_z = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    xela_point_cloud_representation::msg::Texel_<ContainerAllocator> *;
  using ConstRawPtr =
    const xela_point_cloud_representation::msg::Texel_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__xela_point_cloud_representation__msg__Texel
    std::shared_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__xela_point_cloud_representation__msg__Texel
    std::shared_ptr<xela_point_cloud_representation::msg::Texel_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Texel_ & other) const
  {
    if (this->taxel_id != other.taxel_id) {
      return false;
    }
    if (this->sensor_name != other.sensor_name) {
      return false;
    }
    if (this->x != other.x) {
      return false;
    }
    if (this->y != other.y) {
      return false;
    }
    if (this->z != other.z) {
      return false;
    }
    if (this->joint_x != other.joint_x) {
      return false;
    }
    if (this->joint_y != other.joint_y) {
      return false;
    }
    if (this->joint_z != other.joint_z) {
      return false;
    }
    return true;
  }
  bool operator!=(const Texel_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Texel_

// alias to use template instance with default allocator
using Texel =
  xela_point_cloud_representation::msg::Texel_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace xela_point_cloud_representation

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__STRUCT_HPP_
