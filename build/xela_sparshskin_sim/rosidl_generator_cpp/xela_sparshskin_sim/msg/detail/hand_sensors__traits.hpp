// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from xela_sparshskin_sim:msg/HandSensors.idl
// generated code does not contain a copyright notice

#ifndef XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__TRAITS_HPP_
#define XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "xela_sparshskin_sim/msg/detail/hand_sensors__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'texels'
#include "xela_sparshskin_sim/msg/detail/texel__traits.hpp"

namespace xela_sparshskin_sim
{

namespace msg
{

inline void to_flow_style_yaml(
  const HandSensors & msg,
  std::ostream & out)
{
  out << "{";
  // member: texels
  {
    if (msg.texels.size() == 0) {
      out << "texels: []";
    } else {
      out << "texels: [";
      size_t pending_items = msg.texels.size();
      for (auto item : msg.texels) {
        to_flow_style_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const HandSensors & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: texels
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.texels.size() == 0) {
      out << "texels: []\n";
    } else {
      out << "texels:\n";
      for (auto item : msg.texels) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "-\n";
        to_block_style_yaml(item, out, indentation + 2);
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const HandSensors & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace xela_sparshskin_sim

namespace rosidl_generator_traits
{

[[deprecated("use xela_sparshskin_sim::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const xela_sparshskin_sim::msg::HandSensors & msg,
  std::ostream & out, size_t indentation = 0)
{
  xela_sparshskin_sim::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use xela_sparshskin_sim::msg::to_yaml() instead")]]
inline std::string to_yaml(const xela_sparshskin_sim::msg::HandSensors & msg)
{
  return xela_sparshskin_sim::msg::to_yaml(msg);
}

template<>
inline const char * data_type<xela_sparshskin_sim::msg::HandSensors>()
{
  return "xela_sparshskin_sim::msg::HandSensors";
}

template<>
inline const char * name<xela_sparshskin_sim::msg::HandSensors>()
{
  return "xela_sparshskin_sim/msg/HandSensors";
}

template<>
struct has_fixed_size<xela_sparshskin_sim::msg::HandSensors>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<xela_sparshskin_sim::msg::HandSensors>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<xela_sparshskin_sim::msg::HandSensors>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // XELA_SPARSHSKIN_SIM__MSG__DETAIL__HAND_SENSORS__TRAITS_HPP_
