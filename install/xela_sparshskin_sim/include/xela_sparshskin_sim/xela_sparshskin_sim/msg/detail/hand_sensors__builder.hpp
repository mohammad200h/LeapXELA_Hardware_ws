// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from xela_sparshskin_sim:msg/HandSensors.idl
// generated code does not contain a copyright notice

#ifndef XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__BUILDER_HPP_
#define XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "xela_sparshskin_sim/msg/detail/hand_sensors__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace xela_sparshskin_sim
{

namespace msg
{

namespace builder
{

class Init_HandSensors_texels
{
public:
  Init_HandSensors_texels()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::xela_sparshskin_sim::msg::HandSensors texels(::xela_sparshskin_sim::msg::HandSensors::_texels_type arg)
  {
    msg_.texels = std::move(arg);
    return std::move(msg_);
  }

private:
  ::xela_sparshskin_sim::msg::HandSensors msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::xela_sparshskin_sim::msg::HandSensors>()
{
  return xela_sparshskin_sim::msg::builder::Init_HandSensors_texels();
}

}  // namespace xela_sparshskin_sim

#endif  // XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__BUILDER_HPP_
