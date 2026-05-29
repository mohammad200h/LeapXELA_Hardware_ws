// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__TRAITS_HPP_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "xela_point_cloud_representation/msg/detail/texel__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace xela_point_cloud_representation
{

namespace msg
{

inline void to_flow_style_yaml(
  const Texel & msg,
  std::ostream & out)
{
  out << "{";
  // member: taxel_id
  {
    out << "taxel_id: ";
    rosidl_generator_traits::value_to_yaml(msg.taxel_id, out);
    out << ", ";
  }

  // member: sensor_name
  {
    out << "sensor_name: ";
    rosidl_generator_traits::value_to_yaml(msg.sensor_name, out);
    out << ", ";
  }

  // member: x
  {
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << ", ";
  }

  // member: y
  {
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << ", ";
  }

  // member: z
  {
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << ", ";
  }

  // member: joint_x
  {
    out << "joint_x: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_x, out);
    out << ", ";
  }

  // member: joint_y
  {
    out << "joint_y: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_y, out);
    out << ", ";
  }

  // member: joint_z
  {
    out << "joint_z: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_z, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Texel & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: taxel_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "taxel_id: ";
    rosidl_generator_traits::value_to_yaml(msg.taxel_id, out);
    out << "\n";
  }

  // member: sensor_name
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "sensor_name: ";
    rosidl_generator_traits::value_to_yaml(msg.sensor_name, out);
    out << "\n";
  }

  // member: x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << "\n";
  }

  // member: y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << "\n";
  }

  // member: z
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << "\n";
  }

  // member: joint_x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "joint_x: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_x, out);
    out << "\n";
  }

  // member: joint_y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "joint_y: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_y, out);
    out << "\n";
  }

  // member: joint_z
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "joint_z: ";
    rosidl_generator_traits::value_to_yaml(msg.joint_z, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Texel & msg, bool use_flow_style = false)
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

}  // namespace xela_point_cloud_representation

namespace rosidl_generator_traits
{

[[deprecated("use xela_point_cloud_representation::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const xela_point_cloud_representation::msg::Texel & msg,
  std::ostream & out, size_t indentation = 0)
{
  xela_point_cloud_representation::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use xela_point_cloud_representation::msg::to_yaml() instead")]]
inline std::string to_yaml(const xela_point_cloud_representation::msg::Texel & msg)
{
  return xela_point_cloud_representation::msg::to_yaml(msg);
}

template<>
inline const char * data_type<xela_point_cloud_representation::msg::Texel>()
{
  return "xela_point_cloud_representation::msg::Texel";
}

template<>
inline const char * name<xela_point_cloud_representation::msg::Texel>()
{
  return "xela_point_cloud_representation/msg/Texel";
}

template<>
struct has_fixed_size<xela_point_cloud_representation::msg::Texel>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<xela_point_cloud_representation::msg::Texel>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<xela_point_cloud_representation::msg::Texel>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__TRAITS_HPP_
