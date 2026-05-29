// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from xela_point_cloud_representation:msg/HandSensors.idl
// generated code does not contain a copyright notice
#include "xela_point_cloud_representation/msg/detail/hand_sensors__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `texels`
#include "xela_point_cloud_representation/msg/detail/texel__functions.h"

bool
xela_point_cloud_representation__msg__HandSensors__init(xela_point_cloud_representation__msg__HandSensors * msg)
{
  if (!msg) {
    return false;
  }
  // texels
  if (!xela_point_cloud_representation__msg__Texel__Sequence__init(&msg->texels, 0)) {
    xela_point_cloud_representation__msg__HandSensors__fini(msg);
    return false;
  }
  return true;
}

void
xela_point_cloud_representation__msg__HandSensors__fini(xela_point_cloud_representation__msg__HandSensors * msg)
{
  if (!msg) {
    return;
  }
  // texels
  xela_point_cloud_representation__msg__Texel__Sequence__fini(&msg->texels);
}

bool
xela_point_cloud_representation__msg__HandSensors__are_equal(const xela_point_cloud_representation__msg__HandSensors * lhs, const xela_point_cloud_representation__msg__HandSensors * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // texels
  if (!xela_point_cloud_representation__msg__Texel__Sequence__are_equal(
      &(lhs->texels), &(rhs->texels)))
  {
    return false;
  }
  return true;
}

bool
xela_point_cloud_representation__msg__HandSensors__copy(
  const xela_point_cloud_representation__msg__HandSensors * input,
  xela_point_cloud_representation__msg__HandSensors * output)
{
  if (!input || !output) {
    return false;
  }
  // texels
  if (!xela_point_cloud_representation__msg__Texel__Sequence__copy(
      &(input->texels), &(output->texels)))
  {
    return false;
  }
  return true;
}

xela_point_cloud_representation__msg__HandSensors *
xela_point_cloud_representation__msg__HandSensors__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__HandSensors * msg = (xela_point_cloud_representation__msg__HandSensors *)allocator.allocate(sizeof(xela_point_cloud_representation__msg__HandSensors), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(xela_point_cloud_representation__msg__HandSensors));
  bool success = xela_point_cloud_representation__msg__HandSensors__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
xela_point_cloud_representation__msg__HandSensors__destroy(xela_point_cloud_representation__msg__HandSensors * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    xela_point_cloud_representation__msg__HandSensors__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
xela_point_cloud_representation__msg__HandSensors__Sequence__init(xela_point_cloud_representation__msg__HandSensors__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__HandSensors * data = NULL;

  if (size) {
    data = (xela_point_cloud_representation__msg__HandSensors *)allocator.zero_allocate(size, sizeof(xela_point_cloud_representation__msg__HandSensors), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = xela_point_cloud_representation__msg__HandSensors__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        xela_point_cloud_representation__msg__HandSensors__fini(&data[i - 1]);
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
xela_point_cloud_representation__msg__HandSensors__Sequence__fini(xela_point_cloud_representation__msg__HandSensors__Sequence * array)
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
      xela_point_cloud_representation__msg__HandSensors__fini(&array->data[i]);
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

xela_point_cloud_representation__msg__HandSensors__Sequence *
xela_point_cloud_representation__msg__HandSensors__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  xela_point_cloud_representation__msg__HandSensors__Sequence * array = (xela_point_cloud_representation__msg__HandSensors__Sequence *)allocator.allocate(sizeof(xela_point_cloud_representation__msg__HandSensors__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = xela_point_cloud_representation__msg__HandSensors__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
xela_point_cloud_representation__msg__HandSensors__Sequence__destroy(xela_point_cloud_representation__msg__HandSensors__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    xela_point_cloud_representation__msg__HandSensors__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
xela_point_cloud_representation__msg__HandSensors__Sequence__are_equal(const xela_point_cloud_representation__msg__HandSensors__Sequence * lhs, const xela_point_cloud_representation__msg__HandSensors__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!xela_point_cloud_representation__msg__HandSensors__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
xela_point_cloud_representation__msg__HandSensors__Sequence__copy(
  const xela_point_cloud_representation__msg__HandSensors__Sequence * input,
  xela_point_cloud_representation__msg__HandSensors__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(xela_point_cloud_representation__msg__HandSensors);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    xela_point_cloud_representation__msg__HandSensors * data =
      (xela_point_cloud_representation__msg__HandSensors *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!xela_point_cloud_representation__msg__HandSensors__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          xela_point_cloud_representation__msg__HandSensors__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!xela_point_cloud_representation__msg__HandSensors__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
