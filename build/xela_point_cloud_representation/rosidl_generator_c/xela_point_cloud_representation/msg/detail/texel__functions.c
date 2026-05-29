// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from xela_point_cloud_representation:msg/Texel.idl
// generated code does not contain a copyright notice
#include "xela_point_cloud_representation/msg/detail/texel__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `sensor_name`
// Member `joint_x`
// Member `joint_y`
// Member `joint_z`
#include "rosidl_runtime_c/string_functions.h"

bool
xela_point_cloud_representation__msg__Texel__init(xela_point_cloud_representation__msg__Texel * msg)
{
  if (!msg) {
    return false;
  }
  // taxel_id
  // sensor_name
  if (!rosidl_runtime_c__String__init(&msg->sensor_name)) {
    xela_point_cloud_representation__msg__Texel__fini(msg);
    return false;
  }
  // x
  // y
  // z
  // joint_x
  if (!rosidl_runtime_c__String__init(&msg->joint_x)) {
    xela_point_cloud_representation__msg__Texel__fini(msg);
    return false;
  }
  // joint_y
  if (!rosidl_runtime_c__String__init(&msg->joint_y)) {
    xela_point_cloud_representation__msg__Texel__fini(msg);
    return false;
  }
  // joint_z
  if (!rosidl_runtime_c__String__init(&msg->joint_z)) {
    xela_point_cloud_representation__msg__Texel__fini(msg);
    return false;
  }
  return true;
}

void
xela_point_cloud_representation__msg__Texel__fini(xela_point_cloud_representation__msg__Texel * msg)
{
  if (!msg) {
    return;
  }
  // taxel_id
  // sensor_name
  rosidl_runtime_c__String__fini(&msg->sensor_name);
  // x
  // y
  // z
  // joint_x
  rosidl_runtime_c__String__fini(&msg->joint_x);
  // joint_y
  rosidl_runtime_c__String__fini(&msg->joint_y);
  // joint_z
  rosidl_runtime_c__String__fini(&msg->joint_z);
}

bool
xela_point_cloud_representation__msg__Texel__are_equal(const xela_point_cloud_representation__msg__Texel * lhs, const xela_point_cloud_representation__msg__Texel * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // taxel_id
  if (lhs->taxel_id != rhs->taxel_id) {
    return false;
  }
  // sensor_name
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->sensor_name), &(rhs->sensor_name)))
  {
    return false;
  }
  // x
  if (lhs->x != rhs->x) {
    return false;
  }
  // y
  if (lhs->y != rhs->y) {
    return false;
  }
  // z
  if (lhs->z != rhs->z) {
    return false;
  }
  // joint_x
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->joint_x), &(rhs->joint_x)))
  {
    return false;
  }
  // joint_y
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->joint_y), &(rhs->joint_y)))
  {
    return false;
  }
  // joint_z
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->joint_z), &(rhs->joint_z)))
  {
    return false;
  }
  return true;
}

bool
xela_point_cloud_representation__msg__Texel__copy(
  const xela_point_cloud_representation__msg__Texel * input,
  xela_point_cloud_representation__msg__Texel * output)
{
  if (!input || !output) {
    return false;
  }
  // taxel_id
  output->taxel_id = input->taxel_id;
  // sensor_name
  if (!rosidl_runtime_c__String__copy(
      &(input->sensor_name), &(output->sensor_name)))
  {
    return false;
  }
  // x
  output->x = input->x;
  // y
  output->y = input->y;
  // z
  output->z = input->z;
  // joint_x
  if (!rosidl_runtime_c__String__copy(
      &(input->joint_x), &(output->joint_x)))
  {
    return false;
  }
  // joint_y
  if (!rosidl_runtime_c__String__copy(
      &(input->joint_y), &(output->joint_y)))
  {
    return false;
  }
  // joint_z
  if (!rosidl_runtime_c__String__copy(
      &(input->joint_z), &(output->joint_z)))
  {
    return false;
  }
  return true;
}

xela_point_cloud_representation__msg__Texel *
xela_point_cloud_representation__msg__Texel__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__Texel * msg = (xela_point_cloud_representation__msg__Texel *)allocator.allocate(sizeof(xela_point_cloud_representation__msg__Texel), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(xela_point_cloud_representation__msg__Texel));
  bool success = xela_point_cloud_representation__msg__Texel__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
xela_point_cloud_representation__msg__Texel__destroy(xela_point_cloud_representation__msg__Texel * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    xela_point_cloud_representation__msg__Texel__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
xela_point_cloud_representation__msg__Texel__Sequence__init(xela_point_cloud_representation__msg__Texel__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__Texel * data = NULL;

  if (size) {
    data = (xela_point_cloud_representation__msg__Texel *)allocator.zero_allocate(size, sizeof(xela_point_cloud_representation__msg__Texel), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = xela_point_cloud_representation__msg__Texel__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        xela_point_cloud_representation__msg__Texel__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
xela_point_cloud_representation__msg__Texel__Sequence__fini(xela_point_cloud_representation__msg__Texel__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      xela_point_cloud_representation__msg__Texel__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

xela_point_cloud_representation__msg__Texel__Sequence *
xela_point_cloud_representation__msg__Texel__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__Texel__Sequence * array = (xela_point_cloud_representation__msg__Texel__Sequence *)allocator.allocate(sizeof(xela_point_cloud_representation__msg__Texel__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = xela_point_cloud_representation__msg__Texel__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
xela_point_cloud_representation__msg__Texel__Sequence__destroy(xela_point_cloud_representation__msg__Texel__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    xela_point_cloud_representation__msg__Texel__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
xela_point_cloud_representation__msg__Texel__Sequence__are_equal(const xela_point_cloud_representation__msg__Texel__Sequence * lhs, const xela_point_cloud_representation__msg__Texel__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!xela_point_cloud_representation__msg__Texel__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
xela_point_cloud_representation__msg__Texel__Sequence__copy(
  const xela_point_cloud_representation__msg__Texel__Sequence * input,
  xela_point_cloud_representation__msg__Texel__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(xela_point_cloud_representation__msg__Texel);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    xela_point_cloud_representation__msg__Texel * data =
      (xela_point_cloud_representation__msg__Texel *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!xela_point_cloud_representation__msg__Texel__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          xela_point_cloud_representation__msg__Texel__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!xela_point_cloud_representation__msg__Texel__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
