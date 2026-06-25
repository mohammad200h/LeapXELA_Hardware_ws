#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__msg__SceneObject() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__msg__SceneObject__init(msg: *mut SceneObject) -> bool;
    fn arm_server__msg__SceneObject__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SceneObject>, size: usize) -> bool;
    fn arm_server__msg__SceneObject__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SceneObject>);
    fn arm_server__msg__SceneObject__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SceneObject>, out_seq: *mut rosidl_runtime_rs::Sequence<SceneObject>) -> bool;
}

// Corresponds to arm_server__msg__SceneObject
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// Collision object to add to the MoveIt planning scene.

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SceneObject {

    // This member is not documented.
    #[allow(missing_docs)]
    pub id: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape_type: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub dimensions: rosidl_runtime_rs::Sequence<f64>,


    // This member is not documented.
    #[allow(missing_docs)]
    pub x: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub z: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub roll: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub pitch: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub yaw: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub use_color: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub color_r: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub color_g: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub color_b: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub color_a: f32,

}



impl Default for SceneObject {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__msg__SceneObject__init(&mut msg as *mut _) {
        panic!("Call to arm_server__msg__SceneObject__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SceneObject {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__msg__SceneObject__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__msg__SceneObject__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__msg__SceneObject__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SceneObject {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SceneObject where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/msg/SceneObject";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__msg__SceneObject() }
  }
}


