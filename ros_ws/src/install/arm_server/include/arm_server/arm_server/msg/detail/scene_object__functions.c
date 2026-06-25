// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from arm_server:msg/SceneObject.idl
// generated code does not contain a copyright notice
#include "arm_server/msg/detail/scene_object__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `id`
// Member `shape_type`
#include "rosidl_runtime_c/string_functions.h"
// Member `dimensions`
#include "rosidl_runtime_c/primitives_sequence_functions.h"

bool
arm_server__msg__SceneObject__init(arm_server__msg__SceneObject * msg)
{
  if (!msg) {
    return false;
  }
  // id
  if (!rosidl_runtime_c__String__init(&msg->id)) {
    arm_server__msg__SceneObject__fini(msg);
    return false;
  }
  // shape_type
  if (!rosidl_runtime_c__String__init(&msg->shape_type)) {
    arm_server__msg__SceneObject__fini(msg);
    return false;
  }
  // dimensions
  if (!rosidl_runtime_c__double__Sequence__init(&msg->dimensions, 0)) {
    arm_server__msg__SceneObject__fini(msg);
    return false;
  }
  // x
  // y
  // z
  // roll
  // pitch
  // yaw
  // use_color
  // color_r
  // color_g
  // color_b
  // color_a
  return true;
}

void
arm_server__msg__SceneObject__fini(arm_server__msg__SceneObject * msg)
{
  if (!msg) {
    return;
  }
  // id
  rosidl_runtime_c__String__fini(&msg->id);
  // shape_type
  rosidl_runtime_c__String__fini(&msg->shape_type);
  // dimensions
  rosidl_runtime_c__double__Sequence__fini(&msg->dimensions);
  // x
  // y
  // z
  // roll
  // pitch
  // yaw
  // use_color
  // color_r
  // color_g
  // color_b
  // color_a
}

bool
arm_server__msg__SceneObject__are_equal(const arm_server__msg__SceneObject * lhs, const arm_server__msg__SceneObject * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // id
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->id), &(rhs->id)))
  {
    return false;
  }
  // shape_type
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->shape_type), &(rhs->shape_type)))
  {
    return false;
  }
  // dimensions
  if (!rosidl_runtime_c__double__Sequence__are_equal(
      &(lhs->dimensions), &(rhs->dimensions)))
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
  // roll
  if (lhs->roll != rhs->roll) {
    return false;
  }
  // pitch
  if (lhs->pitch != rhs->pitch) {
    return false;
  }
  // yaw
  if (lhs->yaw != rhs->yaw) {
    return false;
  }
  // use_color
  if (lhs->use_color != rhs->use_color) {
    return false;
  }
  // color_r
  if (lhs->color_r != rhs->color_r) {
    return false;
  }
  // color_g
  if (lhs->color_g != rhs->color_g) {
    return false;
  }
  // color_b
  if (lhs->color_b != rhs->color_b) {
    return false;
  }
  // color_a
  if (lhs->color_a != rhs->color_a) {
    return false;
  }
  return true;
}

bool
arm_server__msg__SceneObject__copy(
  const arm_server__msg__SceneObject * input,
  arm_server__msg__SceneObject * output)
{
  if (!input || !output) {
    return false;
  }
  // id
  if (!rosidl_runtime_c__String__copy(
      &(input->id), &(output->id)))
  {
    return false;
  }
  // shape_type
  if (!rosidl_runtime_c__String__copy(
      &(input->shape_type), &(output->shape_type)))
  {
    return false;
  }
  // dimensions
  if (!rosidl_runtime_c__double__Sequence__copy(
      &(input->dimensions), &(output->dimensions)))
  {
    return false;
  }
  // x
  output->x = input->x;
  // y
  output->y = input->y;
  // z
  output->z = input->z;
  // roll
  output->roll = input->roll;
  // pitch
  output->pitch = input->pitch;
  // yaw
  output->yaw = input->yaw;
  // use_color
  output->use_color = input->use_color;
  // color_r
  output->color_r = input->color_r;
  // color_g
  output->color_g = input->color_g;
  // color_b
  output->color_b = input->color_b;
  // color_a
  output->color_a = input->color_a;
  return true;
}

arm_server__msg__SceneObject *
arm_server__msg__SceneObject__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  arm_server__msg__SceneObject * msg = (arm_server__msg__SceneObject *)allocator.allocate(sizeof(arm_server__msg__SceneObject), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(arm_server__msg__SceneObject));
  bool success = arm_server__msg__SceneObject__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
arm_server__msg__SceneObject__destroy(arm_server__msg__SceneObject * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    arm_server__msg__SceneObject__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
arm_server__msg__SceneObject__Sequence__init(arm_server__msg__SceneObject__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  arm_server__msg__SceneObject * data = NULL;

  if (size) {
    data = (arm_server__msg__SceneObject *)allocator.zero_allocate(size, sizeof(arm_server__msg__SceneObject), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = arm_server__msg__SceneObject__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        arm_server__msg__SceneObject__fini(&data[i - 1]);
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
arm_server__msg__SceneObject__Sequence__fini(arm_server__msg__SceneObject__Sequence * array)
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
      arm_server__msg__SceneObject__fini(&array->data[i]);
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

arm_server__msg__SceneObject__Sequence *
arm_server__msg__SceneObject__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  arm_server__msg__SceneObject__Sequence * array = (arm_server__msg__SceneObject__Sequence *)allocator.allocate(sizeof(arm_server__msg__SceneObject__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = arm_server__msg__SceneObject__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
arm_server__msg__SceneObject__Sequence__destroy(arm_server__msg__SceneObject__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    arm_server__msg__SceneObject__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
arm_server__msg__SceneObject__Sequence__are_equal(const arm_server__msg__SceneObject__Sequence * lhs, const arm_server__msg__SceneObject__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!arm_server__msg__SceneObject__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
arm_server__msg__SceneObject__Sequence__copy(
  const arm_server__msg__SceneObject__Sequence * input,
  arm_server__msg__SceneObject__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(arm_server__msg__SceneObject);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    arm_server__msg__SceneObject * data =
      (arm_server__msg__SceneObject *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!arm_server__msg__SceneObject__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          arm_server__msg__SceneObject__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!arm_server__msg__SceneObject__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
