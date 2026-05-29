#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "xela_point_cloud_representation__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__xela_point_cloud_representation__msg__Texel() -> *const std::ffi::c_void;
}

#[link(name = "xela_point_cloud_representation__rosidl_generator_c")]
extern "C" {
    fn xela_point_cloud_representation__msg__Texel__init(msg: *mut Texel) -> bool;
    fn xela_point_cloud_representation__msg__Texel__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Texel>, size: usize) -> bool;
    fn xela_point_cloud_representation__msg__Texel__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Texel>);
    fn xela_point_cloud_representation__msg__Texel__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Texel>, out_seq: *mut rosidl_runtime_rs::Sequence<Texel>) -> bool;
}

// Corresponds to xela_point_cloud_representation__msg__Texel
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Texel {

    // This member is not documented.
    #[allow(missing_docs)]
    pub taxel_id: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub sensor_name: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub x: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub z: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub joint_x: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub joint_y: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub joint_z: rosidl_runtime_rs::String,

}



impl Default for Texel {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !xela_point_cloud_representation__msg__Texel__init(&mut msg as *mut _) {
        panic!("Call to xela_point_cloud_representation__msg__Texel__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Texel {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__Texel__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__Texel__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__Texel__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Texel {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Texel where Self: Sized {
  const TYPE_NAME: &'static str = "xela_point_cloud_representation/msg/Texel";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__xela_point_cloud_representation__msg__Texel() }
  }
}


#[link(name = "xela_point_cloud_representation__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__xela_point_cloud_representation__msg__HandSensors() -> *const std::ffi::c_void;
}

#[link(name = "xela_point_cloud_representation__rosidl_generator_c")]
extern "C" {
    fn xela_point_cloud_representation__msg__HandSensors__init(msg: *mut HandSensors) -> bool;
    fn xela_point_cloud_representation__msg__HandSensors__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<HandSensors>, size: usize) -> bool;
    fn xela_point_cloud_representation__msg__HandSensors__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<HandSensors>);
    fn xela_point_cloud_representation__msg__HandSensors__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<HandSensors>, out_seq: *mut rosidl_runtime_rs::Sequence<HandSensors>) -> bool;
}

// Corresponds to xela_point_cloud_representation__msg__HandSensors
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct HandSensors {

    // This member is not documented.
    #[allow(missing_docs)]
    pub texels: rosidl_runtime_rs::Sequence<super::super::msg::rmw::Texel>,

}



impl Default for HandSensors {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !xela_point_cloud_representation__msg__HandSensors__init(&mut msg as *mut _) {
        panic!("Call to xela_point_cloud_representation__msg__HandSensors__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for HandSensors {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__HandSensors__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__HandSensors__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { xela_point_cloud_representation__msg__HandSensors__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for HandSensors {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for HandSensors where Self: Sized {
  const TYPE_NAME: &'static str = "xela_point_cloud_representation/msg/HandSensors";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__xela_point_cloud_representation__msg__HandSensors() }
  }
}


