// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__BUILDER_HPP_
#define ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "arm_server/msg/detail/scene_object__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace arm_server
{

namespace msg
{

namespace builder
{

class Init_SceneObject_color_a
{
public:
  explicit Init_SceneObject_color_a(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  ::arm_server::msg::SceneObject color_a(::arm_server::msg::SceneObject::_color_a_type arg)
  {
    msg_.color_a = std::move(arg);
    return std::move(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_color_b
{
public:
  explicit Init_SceneObject_color_b(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_color_a color_b(::arm_server::msg::SceneObject::_color_b_type arg)
  {
    msg_.color_b = std::move(arg);
    return Init_SceneObject_color_a(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_color_g
{
public:
  explicit Init_SceneObject_color_g(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_color_b color_g(::arm_server::msg::SceneObject::_color_g_type arg)
  {
    msg_.color_g = std::move(arg);
    return Init_SceneObject_color_b(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_color_r
{
public:
  explicit Init_SceneObject_color_r(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_color_g color_r(::arm_server::msg::SceneObject::_color_r_type arg)
  {
    msg_.color_r = std::move(arg);
    return Init_SceneObject_color_g(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_use_color
{
public:
  explicit Init_SceneObject_use_color(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_color_r use_color(::arm_server::msg::SceneObject::_use_color_type arg)
  {
    msg_.use_color = std::move(arg);
    return Init_SceneObject_color_r(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_yaw
{
public:
  explicit Init_SceneObject_yaw(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_use_color yaw(::arm_server::msg::SceneObject::_yaw_type arg)
  {
    msg_.yaw = std::move(arg);
    return Init_SceneObject_use_color(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_pitch
{
public:
  explicit Init_SceneObject_pitch(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_yaw pitch(::arm_server::msg::SceneObject::_pitch_type arg)
  {
    msg_.pitch = std::move(arg);
    return Init_SceneObject_yaw(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_roll
{
public:
  explicit Init_SceneObject_roll(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_pitch roll(::arm_server::msg::SceneObject::_roll_type arg)
  {
    msg_.roll = std::move(arg);
    return Init_SceneObject_pitch(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_z
{
public:
  explicit Init_SceneObject_z(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_roll z(::arm_server::msg::SceneObject::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_SceneObject_roll(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_y
{
public:
  explicit Init_SceneObject_y(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_z y(::arm_server::msg::SceneObject::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_SceneObject_z(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_x
{
public:
  explicit Init_SceneObject_x(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_y x(::arm_server::msg::SceneObject::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_SceneObject_y(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_dimensions
{
public:
  explicit Init_SceneObject_dimensions(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_x dimensions(::arm_server::msg::SceneObject::_dimensions_type arg)
  {
    msg_.dimensions = std::move(arg);
    return Init_SceneObject_x(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_shape_type
{
public:
  explicit Init_SceneObject_shape_type(::arm_server::msg::SceneObject & msg)
  : msg_(msg)
  {}
  Init_SceneObject_dimensions shape_type(::arm_server::msg::SceneObject::_shape_type_type arg)
  {
    msg_.shape_type = std::move(arg);
    return Init_SceneObject_dimensions(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

class Init_SceneObject_id
{
public:
  Init_SceneObject_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SceneObject_shape_type id(::arm_server::msg::SceneObject::_id_type arg)
  {
    msg_.id = std::move(arg);
    return Init_SceneObject_shape_type(msg_);
  }

private:
  ::arm_server::msg::SceneObject msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::arm_server::msg::SceneObject>()
{
  return arm_server::msg::builder::Init_SceneObject_id();
}

}  // namespace arm_server

#endif  // ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__BUILDER_HPP_
