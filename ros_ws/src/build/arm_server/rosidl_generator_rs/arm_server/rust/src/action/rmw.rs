
#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Goal() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_Goal__init(msg: *mut Plan_Goal) -> bool;
    fn arm_server__action__Plan_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_Goal>, size: usize) -> bool;
    fn arm_server__action__Plan_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_Goal>);
    fn arm_server__action__Plan_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_Goal>) -> bool;
}

// Corresponds to arm_server__action__Plan_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_Goal {

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

}



impl Default for Plan_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_Goal__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Goal() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Result() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_Result__init(msg: *mut Plan_Result) -> bool;
    fn arm_server__action__Plan_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_Result>, size: usize) -> bool;
    fn arm_server__action__Plan_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_Result>);
    fn arm_server__action__Plan_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_Result>) -> bool;
}

// Corresponds to arm_server__action__Plan_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub plan_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub trajectory_duration: f64,

}



impl Default for Plan_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_Result__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_Result where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Result() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_Feedback__init(msg: *mut Plan_Feedback) -> bool;
    fn arm_server__action__Plan_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_Feedback>, size: usize) -> bool;
    fn arm_server__action__Plan_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_Feedback>);
    fn arm_server__action__Plan_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_Feedback>) -> bool;
}

// Corresponds to arm_server__action__Plan_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_Feedback {

    // This member is not documented.
    #[allow(missing_docs)]
    pub progress: f64,

}



impl Default for Plan_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_Feedback__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_Feedback() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_FeedbackMessage__init(msg: *mut Plan_FeedbackMessage) -> bool;
    fn arm_server__action__Plan_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_FeedbackMessage>, size: usize) -> bool;
    fn arm_server__action__Plan_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_FeedbackMessage>);
    fn arm_server__action__Plan_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_FeedbackMessage>) -> bool;
}

// Corresponds to arm_server__action__Plan_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::Plan_Feedback,

}



impl Default for Plan_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_FeedbackMessage() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Goal() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_Goal__init(msg: *mut Execute_Goal) -> bool;
    fn arm_server__action__Execute_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_Goal>, size: usize) -> bool;
    fn arm_server__action__Execute_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_Goal>);
    fn arm_server__action__Execute_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_Goal>) -> bool;
}

// Corresponds to arm_server__action__Execute_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_Goal {

    // This member is not documented.
    #[allow(missing_docs)]
    pub plan_id: u64,

}



impl Default for Execute_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_Goal__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Goal() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Result() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_Result__init(msg: *mut Execute_Result) -> bool;
    fn arm_server__action__Execute_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_Result>, size: usize) -> bool;
    fn arm_server__action__Execute_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_Result>);
    fn arm_server__action__Execute_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_Result>) -> bool;
}

// Corresponds to arm_server__action__Execute_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,

}



impl Default for Execute_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_Result__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_Result where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Result() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_Feedback__init(msg: *mut Execute_Feedback) -> bool;
    fn arm_server__action__Execute_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_Feedback>, size: usize) -> bool;
    fn arm_server__action__Execute_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_Feedback>);
    fn arm_server__action__Execute_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_Feedback>) -> bool;
}

// Corresponds to arm_server__action__Execute_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_Feedback {

    // This member is not documented.
    #[allow(missing_docs)]
    pub progress: f64,

}



impl Default for Execute_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_Feedback__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_Feedback() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_FeedbackMessage__init(msg: *mut Execute_FeedbackMessage) -> bool;
    fn arm_server__action__Execute_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_FeedbackMessage>, size: usize) -> bool;
    fn arm_server__action__Execute_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_FeedbackMessage>);
    fn arm_server__action__Execute_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_FeedbackMessage>) -> bool;
}

// Corresponds to arm_server__action__Execute_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::Execute_Feedback,

}



impl Default for Execute_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_FeedbackMessage() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Goal() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_Goal__init(msg: *mut UpdatePlanningScene_Goal) -> bool;
    fn arm_server__action__UpdatePlanningScene_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Goal>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Goal>);
    fn arm_server__action__UpdatePlanningScene_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Goal>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_Goal {

    // This member is not documented.
    #[allow(missing_docs)]
    pub objects: rosidl_runtime_rs::Sequence<super::super::msg::rmw::SceneObject>,


    // This member is not documented.
    #[allow(missing_docs)]
    pub clear_existing: bool,

}



impl Default for UpdatePlanningScene_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_Goal__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Goal() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Result() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_Result__init(msg: *mut UpdatePlanningScene_Result) -> bool;
    fn arm_server__action__UpdatePlanningScene_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Result>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Result>);
    fn arm_server__action__UpdatePlanningScene_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Result>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub objects_added: u32,

}



impl Default for UpdatePlanningScene_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_Result__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_Result where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Result() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_Feedback__init(msg: *mut UpdatePlanningScene_Feedback) -> bool;
    fn arm_server__action__UpdatePlanningScene_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Feedback>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Feedback>);
    fn arm_server__action__UpdatePlanningScene_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_Feedback>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_Feedback {

    // This member is not documented.
    #[allow(missing_docs)]
    pub progress: f64,

}



impl Default for UpdatePlanningScene_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_Feedback__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_Feedback() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_FeedbackMessage__init(msg: *mut UpdatePlanningScene_FeedbackMessage) -> bool;
    fn arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_FeedbackMessage>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_FeedbackMessage>);
    fn arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_FeedbackMessage>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::UpdatePlanningScene_Feedback,

}



impl Default for UpdatePlanningScene_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_FeedbackMessage() }
  }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_SendGoal_Request__init(msg: *mut Plan_SendGoal_Request) -> bool;
    fn arm_server__action__Plan_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Request>, size: usize) -> bool;
    fn arm_server__action__Plan_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Request>);
    fn arm_server__action__Plan_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Request>) -> bool;
}

// Corresponds to arm_server__action__Plan_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::Plan_Goal,

}



impl Default for Plan_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_SendGoal_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_SendGoal_Response__init(msg: *mut Plan_SendGoal_Response) -> bool;
    fn arm_server__action__Plan_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Response>, size: usize) -> bool;
    fn arm_server__action__Plan_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Response>);
    fn arm_server__action__Plan_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_SendGoal_Response>) -> bool;
}

// Corresponds to arm_server__action__Plan_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for Plan_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_SendGoal_Response() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_GetResult_Request__init(msg: *mut Plan_GetResult_Request) -> bool;
    fn arm_server__action__Plan_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Request>, size: usize) -> bool;
    fn arm_server__action__Plan_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Request>);
    fn arm_server__action__Plan_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Request>) -> bool;
}

// Corresponds to arm_server__action__Plan_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for Plan_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_GetResult_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Plan_GetResult_Response__init(msg: *mut Plan_GetResult_Response) -> bool;
    fn arm_server__action__Plan_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Response>, size: usize) -> bool;
    fn arm_server__action__Plan_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Response>);
    fn arm_server__action__Plan_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Plan_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<Plan_GetResult_Response>) -> bool;
}

// Corresponds to arm_server__action__Plan_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Plan_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::Plan_Result,

}



impl Default for Plan_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Plan_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Plan_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Plan_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Plan_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Plan_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Plan_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Plan_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Plan_GetResult_Response() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_SendGoal_Request__init(msg: *mut Execute_SendGoal_Request) -> bool;
    fn arm_server__action__Execute_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Request>, size: usize) -> bool;
    fn arm_server__action__Execute_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Request>);
    fn arm_server__action__Execute_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Request>) -> bool;
}

// Corresponds to arm_server__action__Execute_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::Execute_Goal,

}



impl Default for Execute_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_SendGoal_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_SendGoal_Response__init(msg: *mut Execute_SendGoal_Response) -> bool;
    fn arm_server__action__Execute_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Response>, size: usize) -> bool;
    fn arm_server__action__Execute_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Response>);
    fn arm_server__action__Execute_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_SendGoal_Response>) -> bool;
}

// Corresponds to arm_server__action__Execute_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for Execute_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_SendGoal_Response() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_GetResult_Request__init(msg: *mut Execute_GetResult_Request) -> bool;
    fn arm_server__action__Execute_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Request>, size: usize) -> bool;
    fn arm_server__action__Execute_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Request>);
    fn arm_server__action__Execute_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Request>) -> bool;
}

// Corresponds to arm_server__action__Execute_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for Execute_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_GetResult_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__Execute_GetResult_Response__init(msg: *mut Execute_GetResult_Response) -> bool;
    fn arm_server__action__Execute_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Response>, size: usize) -> bool;
    fn arm_server__action__Execute_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Response>);
    fn arm_server__action__Execute_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Execute_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<Execute_GetResult_Response>) -> bool;
}

// Corresponds to arm_server__action__Execute_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Execute_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::Execute_Result,

}



impl Default for Execute_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__Execute_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__Execute_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Execute_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__Execute_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Execute_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Execute_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/Execute_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__Execute_GetResult_Response() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_SendGoal_Request__init(msg: *mut UpdatePlanningScene_SendGoal_Request) -> bool;
    fn arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Request>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Request>);
    fn arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Request>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::UpdatePlanningScene_Goal,

}



impl Default for UpdatePlanningScene_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_SendGoal_Response__init(msg: *mut UpdatePlanningScene_SendGoal_Response) -> bool;
    fn arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Response>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Response>);
    fn arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_SendGoal_Response>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for UpdatePlanningScene_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal_Response() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_GetResult_Request__init(msg: *mut UpdatePlanningScene_GetResult_Request) -> bool;
    fn arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Request>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Request>);
    fn arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Request>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for UpdatePlanningScene_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult_Request() }
  }
}


#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "arm_server__rosidl_generator_c")]
extern "C" {
    fn arm_server__action__UpdatePlanningScene_GetResult_Response__init(msg: *mut UpdatePlanningScene_GetResult_Response) -> bool;
    fn arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Response>, size: usize) -> bool;
    fn arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Response>);
    fn arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<UpdatePlanningScene_GetResult_Response>) -> bool;
}

// Corresponds to arm_server__action__UpdatePlanningScene_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct UpdatePlanningScene_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::UpdatePlanningScene_Result,

}



impl Default for UpdatePlanningScene_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !arm_server__action__UpdatePlanningScene_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to arm_server__action__UpdatePlanningScene_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for UpdatePlanningScene_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { arm_server__action__UpdatePlanningScene_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for UpdatePlanningScene_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for UpdatePlanningScene_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "arm_server/action/UpdatePlanningScene_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult_Response() }
  }
}






#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Plan_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__Plan_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct Plan_SendGoal;

impl rosidl_runtime_rs::Service for Plan_SendGoal {
    type Request = Plan_SendGoal_Request;
    type Response = Plan_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Plan_SendGoal() }
    }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Plan_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__Plan_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct Plan_GetResult;

impl rosidl_runtime_rs::Service for Plan_GetResult {
    type Request = Plan_GetResult_Request;
    type Response = Plan_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Plan_GetResult() }
    }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Execute_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__Execute_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct Execute_SendGoal;

impl rosidl_runtime_rs::Service for Execute_SendGoal {
    type Request = Execute_SendGoal_Request;
    type Response = Execute_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Execute_SendGoal() }
    }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Execute_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__Execute_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct Execute_GetResult;

impl rosidl_runtime_rs::Service for Execute_GetResult {
    type Request = Execute_GetResult_Request;
    type Response = Execute_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__Execute_GetResult() }
    }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__UpdatePlanningScene_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct UpdatePlanningScene_SendGoal;

impl rosidl_runtime_rs::Service for UpdatePlanningScene_SendGoal {
    type Request = UpdatePlanningScene_SendGoal_Request;
    type Response = UpdatePlanningScene_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__UpdatePlanningScene_SendGoal() }
    }
}




#[link(name = "arm_server__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to arm_server__action__UpdatePlanningScene_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct UpdatePlanningScene_GetResult;

impl rosidl_runtime_rs::Service for UpdatePlanningScene_GetResult {
    type Request = UpdatePlanningScene_GetResult_Request;
    type Response = UpdatePlanningScene_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__arm_server__action__UpdatePlanningScene_GetResult() }
    }
}


