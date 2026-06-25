#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to arm_server__msg__SceneObject
/// Collision object to add to the MoveIt planning scene.

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SceneObject {

    // This member is not documented.
    #[allow(missing_docs)]
    pub id: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape_type: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub dimensions: Vec<f64>,


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
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::SceneObject::default())
  }
}

impl rosidl_runtime_rs::Message for SceneObject {
  type RmwMsg = super::msg::rmw::SceneObject;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        id: msg.id.as_str().into(),
        shape_type: msg.shape_type.as_str().into(),
        dimensions: msg.dimensions.into(),
        x: msg.x,
        y: msg.y,
        z: msg.z,
        roll: msg.roll,
        pitch: msg.pitch,
        yaw: msg.yaw,
        use_color: msg.use_color,
        color_r: msg.color_r,
        color_g: msg.color_g,
        color_b: msg.color_b,
        color_a: msg.color_a,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        id: msg.id.as_str().into(),
        shape_type: msg.shape_type.as_str().into(),
        dimensions: msg.dimensions.as_slice().into(),
      x: msg.x,
      y: msg.y,
      z: msg.z,
      roll: msg.roll,
      pitch: msg.pitch,
      yaw: msg.yaw,
      use_color: msg.use_color,
      color_r: msg.color_r,
      color_g: msg.color_g,
      color_b: msg.color_b,
      color_a: msg.color_a,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      id: msg.id.to_string(),
      shape_type: msg.shape_type.to_string(),
      dimensions: msg.dimensions
          .into_iter()
          .collect(),
      x: msg.x,
      y: msg.y,
      z: msg.z,
      roll: msg.roll,
      pitch: msg.pitch,
      yaw: msg.yaw,
      use_color: msg.use_color,
      color_r: msg.color_r,
      color_g: msg.color_g,
      color_b: msg.color_b,
      color_a: msg.color_a,
    }
  }
}


