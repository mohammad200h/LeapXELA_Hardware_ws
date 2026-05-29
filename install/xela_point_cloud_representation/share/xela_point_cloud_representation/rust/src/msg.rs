#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to xela_point_cloud_representation__msg__Texel

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Texel {

    // This member is not documented.
    #[allow(missing_docs)]
    pub taxel_id: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub sensor_name: std::string::String,


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
    pub joint_x: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub joint_y: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub joint_z: std::string::String,

}



impl Default for Texel {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::Texel::default())
  }
}

impl rosidl_runtime_rs::Message for Texel {
  type RmwMsg = super::msg::rmw::Texel;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        taxel_id: msg.taxel_id,
        sensor_name: msg.sensor_name.as_str().into(),
        x: msg.x,
        y: msg.y,
        z: msg.z,
        joint_x: msg.joint_x.as_str().into(),
        joint_y: msg.joint_y.as_str().into(),
        joint_z: msg.joint_z.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      taxel_id: msg.taxel_id,
        sensor_name: msg.sensor_name.as_str().into(),
      x: msg.x,
      y: msg.y,
      z: msg.z,
        joint_x: msg.joint_x.as_str().into(),
        joint_y: msg.joint_y.as_str().into(),
        joint_z: msg.joint_z.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      taxel_id: msg.taxel_id,
      sensor_name: msg.sensor_name.to_string(),
      x: msg.x,
      y: msg.y,
      z: msg.z,
      joint_x: msg.joint_x.to_string(),
      joint_y: msg.joint_y.to_string(),
      joint_z: msg.joint_z.to_string(),
    }
  }
}


// Corresponds to xela_point_cloud_representation__msg__HandSensors

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct HandSensors {

    // This member is not documented.
    #[allow(missing_docs)]
    pub texels: Vec<super::msg::Texel>,

}



impl Default for HandSensors {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::HandSensors::default())
  }
}

impl rosidl_runtime_rs::Message for HandSensors {
  type RmwMsg = super::msg::rmw::HandSensors;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        texels: msg.texels
          .into_iter()
          .map(|elem| super::msg::Texel::into_rmw_message(std::borrow::Cow::Owned(elem)).into_owned())
          .collect(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        texels: msg.texels
          .iter()
          .map(|elem| super::msg::Texel::into_rmw_message(std::borrow::Cow::Borrowed(elem)).into_owned())
          .collect(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      texels: msg.texels
          .into_iter()
          .map(super::msg::Texel::from_rmw_message)
          .collect(),
    }
  }
}


