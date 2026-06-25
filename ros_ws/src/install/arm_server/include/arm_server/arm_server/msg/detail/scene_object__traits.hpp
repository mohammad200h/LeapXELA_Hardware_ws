// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice

#ifndef ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__TRAITS_HPP_
#define ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "arm_server/msg/detail/scene_object__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace arm_server
{

namespace msg
{

inline void to_flow_style_yaml(
  const SceneObject & msg,
  std::ostream & out)
{
  out << "{";
  // member: id
  {
    out << "id: ";
    rosidl_generator_traits::value_to_yaml(msg.id, out);
    out << ", ";
  }

  // member: shape_type
  {
    out << "shape_type: ";
    rosidl_generator_traits::value_to_yaml(msg.shape_type, out);
    out << ", ";
  }

  // member: dimensions
  {
    if (msg.dimensions.size() == 0) {
      out << "dimensions: []";
    } else {
      out << "dimensions: [";
      size_t pending_items = msg.dimensions.size();
      for (auto item : msg.dimensions) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
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

  // member: roll
  {
    out << "roll: ";
    rosidl_generator_traits::value_to_yaml(msg.roll, out);
    out << ", ";
  }

  // member: pitch
  {
    out << "pitch: ";
    rosidl_generator_traits::value_to_yaml(msg.pitch, out);
    out << ", ";
  }

  // member: yaw
  {
    out << "yaw: ";
    rosidl_generator_traits::value_to_yaml(msg.yaw, out);
    out << ", ";
  }

  // member: use_color
  {
    out << "use_color: ";
    rosidl_generator_traits::value_to_yaml(msg.use_color, out);
    out << ", ";
  }

  // member: color_r
  {
    out << "color_r: ";
    rosidl_generator_traits::value_to_yaml(msg.color_r, out);
    out << ", ";
  }

  // member: color_g
  {
    out << "color_g: ";
    rosidl_generator_traits::value_to_yaml(msg.color_g, out);
    out << ", ";
  }

  // member: color_b
  {
    out << "color_b: ";
    rosidl_generator_traits::value_to_yaml(msg.color_b, out);
    out << ", ";
  }

  // member: color_a
  {
    out << "color_a: ";
    rosidl_generator_traits::value_to_yaml(msg.color_a, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SceneObject & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "id: ";
    rosidl_generator_traits::value_to_yaml(msg.id, out);
    out << "\n";
  }

  // member: shape_type
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "shape_type: ";
    rosidl_generator_traits::value_to_yaml(msg.shape_type, out);
    out << "\n";
  }

  // member: dimensions
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.dimensions.size() == 0) {
      out << "dimensions: []\n";
    } else {
      out << "dimensions:\n";
      for (auto item : msg.dimensions) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
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

  // member: roll
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "roll: ";
    rosidl_generator_traits::value_to_yaml(msg.roll, out);
    out << "\n";
  }

  // member: pitch
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pitch: ";
    rosidl_generator_traits::value_to_yaml(msg.pitch, out);
    out << "\n";
  }

  // member: yaw
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "yaw: ";
    rosidl_generator_traits::value_to_yaml(msg.yaw, out);
    out << "\n";
  }

  // member: use_color
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "use_color: ";
    rosidl_generator_traits::value_to_yaml(msg.use_color, out);
    out << "\n";
  }

  // member: color_r
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "color_r: ";
    rosidl_generator_traits::value_to_yaml(msg.color_r, out);
    out << "\n";
  }

  // member: color_g
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "color_g: ";
    rosidl_generator_traits::value_to_yaml(msg.color_g, out);
    out << "\n";
  }

  // member: color_b
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "color_b: ";
    rosidl_generator_traits::value_to_yaml(msg.color_b, out);
    out << "\n";
  }

  // member: color_a
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "color_a: ";
    rosidl_generator_traits::value_to_yaml(msg.color_a, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SceneObject & msg, bool use_flow_style = false)
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

}  // namespace arm_server

namespace rosidl_generator_traits
{

[[deprecated("use arm_server::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const arm_server::msg::SceneObject & msg,
  std::ostream & out, size_t indentation = 0)
{
  arm_server::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use arm_server::msg::to_yaml() instead")]]
inline std::string to_yaml(const arm_server::msg::SceneObject & msg)
{
  return arm_server::msg::to_yaml(msg);
}

template<>
inline const char * data_type<arm_server::msg::SceneObject>()
{
  return "arm_server::msg::SceneObject";
}

template<>
inline const char * name<arm_server::msg::SceneObject>()
{
  return "arm_server/msg/SceneObject";
}

template<>
struct has_fixed_size<arm_server::msg::SceneObject>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<arm_server::msg::SceneObject>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<arm_server::msg::SceneObject>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // ARM_SERVER__MSG__DETAIL__SCENE_OBJECT__TRAITS_HPP_
