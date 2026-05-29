// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice

#ifndef XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__FUNCTIONS_H_
#define XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "xela_point_cloud_representation/msg/rosidl_generator_c__visibility_control.h"

#include "xela_point_cloud_representation/msg/detail/texel__struct.h"

/// Initialize msg/Texel message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * xela_point_cloud_representation__msg__Texel
 * )) before or use
 * xela_point_cloud_representation__msg__Texel__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__init(xela_point_cloud_representation__msg__Texel * msg);

/// Finalize msg/Texel message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
void
xela_point_cloud_representation__msg__Texel__fini(xela_point_cloud_representation__msg__Texel * msg);

/// Create msg/Texel message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * xela_point_cloud_representation__msg__Texel__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
xela_point_cloud_representation__msg__Texel *
xela_point_cloud_representation__msg__Texel__create();

/// Destroy msg/Texel message.
/**
 * It calls
 * xela_point_cloud_representation__msg__Texel__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
void
xela_point_cloud_representation__msg__Texel__destroy(xela_point_cloud_representation__msg__Texel * msg);

/// Check for msg/Texel message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__are_equal(const xela_point_cloud_representation__msg__Texel * lhs, const xela_point_cloud_representation__msg__Texel * rhs);

/// Copy a msg/Texel message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__copy(
  const xela_point_cloud_representation__msg__Texel * input,
  xela_point_cloud_representation__msg__Texel * output);

/// Initialize array of msg/Texel messages.
/**
 * It allocates the memory for the number of elements and calls
 * xela_point_cloud_representation__msg__Texel__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__Sequence__init(xela_point_cloud_representation__msg__Texel__Sequence * array, size_t size);

/// Finalize array of msg/Texel messages.
/**
 * It calls
 * xela_point_cloud_representation__msg__Texel__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
void
xela_point_cloud_representation__msg__Texel__Sequence__fini(xela_point_cloud_representation__msg__Texel__Sequence * array);

/// Create array of msg/Texel messages.
/**
 * It allocates the memory for the array and calls
 * xela_point_cloud_representation__msg__Texel__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
xela_point_cloud_representation__msg__Texel__Sequence *
xela_point_cloud_representation__msg__Texel__Sequence__create(size_t size);

/// Destroy array of msg/Texel messages.
/**
 * It calls
 * xela_point_cloud_representation__msg__Texel__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
void
xela_point_cloud_representation__msg__Texel__Sequence__destroy(xela_point_cloud_representation__msg__Texel__Sequence * array);

/// Check for msg/Texel message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__Sequence__are_equal(const xela_point_cloud_representation__msg__Texel__Sequence * lhs, const xela_point_cloud_representation__msg__Texel__Sequence * rhs);

/// Copy an array of msg/Texel messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_xela_point_cloud_representation
bool
xela_point_cloud_representation__msg__Texel__Sequence__copy(
  const xela_point_cloud_representation__msg__Texel__Sequence * input,
  xela_point_cloud_representation__msg__Texel__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // XELA_POINT_CLOUD_REPRESENTATION__MSG__DETAIL__TEXEL__FUNCTIONS_H_
