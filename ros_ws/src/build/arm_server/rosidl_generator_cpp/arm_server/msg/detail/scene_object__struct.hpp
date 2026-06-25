// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_HPP_
#define ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__arm_server__msg__SceneObject __attribute__((deprecated))
#else
# define DEPRECATED__arm_server__msg__SceneObject __declspec(deprecated)
#endif

namespace arm_server
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct SceneObject_
{
  using Type = SceneObject_<ContainerAllocator>;

  explicit SceneObject_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = "";
      this->shape_type = "";
      this->x = 0.0;
      this->y = 0.0;
      this->z = 0.0;
      this->roll = 0.0;
      this->pitch = 0.0;
      this->yaw = 0.0;
      this->use_color = false;
      this->color_r = 0.0f;
      this->color_g = 0.0f;
      this->color_b = 0.0f;
      this->color_a = 0.0f;
    }
  }

  explicit SceneObject_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : id(_alloc),
    shape_type(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = "";
      this->shape_type = "";
      this->x = 0.0;
      this->y = 0.0;
      this->z = 0.0;
      this->roll = 0.0;
      this->pitch = 0.0;
      this->yaw = 0.0;
      this->use_color = false;
      this->color_r = 0.0f;
      this->color_g = 0.0f;
      this->color_b = 0.0f;
      this->color_a = 0.0f;
    }
  }

  // field types and members
  using _id_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _id_type id;
  using _shape_type_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _shape_type_type shape_type;
  using _dimensions_type =
    std::vector<double, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<double>>;
  _dimensions_type dimensions;
  using _x_type =
    double;
  _x_type x;
  using _y_type =
    double;
  _y_type y;
  using _z_type =
    double;
  _z_type z;
  using _roll_type =
    double;
  _roll_type roll;
  using _pitch_type =
    double;
  _pitch_type pitch;
  using _yaw_type =
    double;
  _yaw_type yaw;
  using _use_color_type =
    bool;
  _use_color_type use_color;
  using _color_r_type =
    float;
  _color_r_type color_r;
  using _color_g_type =
    float;
  _color_g_type color_g;
  using _color_b_type =
    float;
  _color_b_type color_b;
  using _color_a_type =
    float;
  _color_a_type color_a;

  // setters for named parameter idiom
  Type & set__id(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->id = _arg;
    return *this;
  }
  Type & set__shape_type(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->shape_type = _arg;
    return *this;
  }
  Type & set__dimensions(
    const std::vector<double, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<double>> & _arg)
  {
    this->dimensions = _arg;
    return *this;
  }
  Type & set__x(
    const double & _arg)
  {
    this->x = _arg;
    return *this;
  }
  Type & set__y(
    const double & _arg)
  {
    this->y = _arg;
    return *this;
  }
  Type & set__z(
    const double & _arg)
  {
    this->z = _arg;
    return *this;
  }
  Type & set__roll(
    const double & _arg)
  {
    this->roll = _arg;
    return *this;
  }
  Type & set__pitch(
    const double & _arg)
  {
    this->pitch = _arg;
    return *this;
  }
  Type & set__yaw(
    const double & _arg)
  {
    this->yaw = _arg;
    return *this;
  }
  Type & set__use_color(
    const bool & _arg)
  {
    this->use_color = _arg;
    return *this;
  }
  Type & set__color_r(
    const float & _arg)
  {
    this->color_r = _arg;
    return *this;
  }
  Type & set__color_g(
    const float & _arg)
  {
    this->color_g = _arg;
    return *this;
  }
  Type & set__color_b(
    const float & _arg)
  {
    this->color_b = _arg;
    return *this;
  }
  Type & set__color_a(
    const float & _arg)
  {
    this->color_a = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    arm_server::msg::SceneObject_<ContainerAllocator> *;
  using ConstRawPtr =
    const arm_server::msg::SceneObject_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<arm_server::msg::SceneObject_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<arm_server::msg::SceneObject_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      arm_server::msg::SceneObject_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<arm_server::msg::SceneObject_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      arm_server::msg::SceneObject_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<arm_server::msg::SceneObject_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<arm_server::msg::SceneObject_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<arm_server::msg::SceneObject_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__arm_server__msg__SceneObject
    std::shared_ptr<arm_server::msg::SceneObject_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__arm_server__msg__SceneObject
    std::shared_ptr<arm_server::msg::SceneObject_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SceneObject_ & other) const
  {
    if (this->id != other.id) {
      return false;
    }
    if (this->shape_type != other.shape_type) {
      return false;
    }
    if (this->dimensions != other.dimensions) {
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
    if (this->roll != other.roll) {
      return false;
    }
    if (this->pitch != other.pitch) {
      return false;
    }
    if (this->yaw != other.yaw) {
      return false;
    }
    if (this->use_color != other.use_color) {
      return false;
    }
    if (this->color_r != other.color_r) {
      return false;
    }
    if (this->color_g != other.color_g) {
      return false;
    }
    if (this->color_b != other.color_b) {
      return false;
    }
    if (this->color_a != other.color_a) {
      return false;
    }
    return true;
  }
  bool operator!=(const SceneObject_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SceneObject_

// alias to use template instance with default allocator
using SceneObject =
  arm_server::msg::SceneObject_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace arm_server

#endif  // ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__STRUCT_HPP_
