// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__BUILDER_HPP_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "xela_point_cloud_representation/msg/detail/texel__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace xela_point_cloud_representation
{

namespace msg
{

namespace builder
{

class Init_Texel_joint_z
{
public:
  explicit Init_Texel_joint_z(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  ::xela_point_cloud_representation::msg::Texel joint_z(::xela_point_cloud_representation::msg::Texel::_joint_z_type arg)
  {
    msg_.joint_z = std::move(arg);
    return std::move(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_joint_y
{
public:
  explicit Init_Texel_joint_y(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_joint_z joint_y(::xela_point_cloud_representation::msg::Texel::_joint_y_type arg)
  {
    msg_.joint_y = std::move(arg);
    return Init_Texel_joint_z(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_joint_x
{
public:
  explicit Init_Texel_joint_x(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_joint_y joint_x(::xela_point_cloud_representation::msg::Texel::_joint_x_type arg)
  {
    msg_.joint_x = std::move(arg);
    return Init_Texel_joint_y(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_z
{
public:
  explicit Init_Texel_z(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_joint_x z(::xela_point_cloud_representation::msg::Texel::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_Texel_joint_x(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_y
{
public:
  explicit Init_Texel_y(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_z y(::xela_point_cloud_representation::msg::Texel::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_Texel_z(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_x
{
public:
  explicit Init_Texel_x(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_y x(::xela_point_cloud_representation::msg::Texel::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_Texel_y(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_sensor_name
{
public:
  explicit Init_Texel_sensor_name(::xela_point_cloud_representation::msg::Texel & msg)
  : msg_(msg)
  {}
  Init_Texel_x sensor_name(::xela_point_cloud_representation::msg::Texel::_sensor_name_type arg)
  {
    msg_.sensor_name = std::move(arg);
    return Init_Texel_x(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

class Init_Texel_taxel_id
{
public:
  Init_Texel_taxel_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Texel_sensor_name taxel_id(::xela_point_cloud_representation::msg::Texel::_taxel_id_type arg)
  {
    msg_.taxel_id = std::move(arg);
    return Init_Texel_sensor_name(msg_);
  }

private:
  ::xela_point_cloud_representation::msg::Texel msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::xela_point_cloud_representation::msg::Texel>()
{
  return xela_point_cloud_representation::msg::builder::Init_Texel_taxel_id();
}

}  // namespace xela_point_cloud_representation

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__BUILDER_HPP_
