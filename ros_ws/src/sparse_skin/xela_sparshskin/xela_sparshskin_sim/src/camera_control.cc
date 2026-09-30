#include <xela_sparshskin_sim/camera_control.hpp>

#include <algorithm>
#include <cmath>

namespace xela_sparshskin_sim
{
namespace
{
constexpr double kDoubleClickSec = 0.25;
}  // namespace

CameraControl::CameraControl(
  GLFWwindow * window,
  mjModel * model,
  mjData * data,
  mjvCamera * camera,
  mjvOption * opt,
  mjvScene * scene,
  mjvPerturb * pert,
  MoveCameraFn mjv_moveCamera,
  DefaultCameraFn mjv_defaultCamera,
  std::mutex * mj_mutex,
  AdhesionToggledFn on_adhesion_toggled)
: window_(window),
  model_(model),
  data_(data),
  camera_(camera),
  opt_(opt),
  scene_(scene),
  pert_(pert),
  mjv_moveCamera_(mjv_moveCamera),
  mjv_defaultCamera_(mjv_defaultCamera),
  mj_mutex_(mj_mutex),
  on_adhesion_toggled_(std::move(on_adhesion_toggled))
{
}

void CameraControl::install()
{
  if (!window_) {
    return;
  }
  glfwSetWindowUserPointer(window_, this);
  glfwSetMouseButtonCallback(window_, &CameraControl::cb_mouse_button);
  glfwSetCursorPosCallback(window_, &CameraControl::cb_mouse_move);
  glfwSetScrollCallback(window_, &CameraControl::cb_scroll);
  glfwSetKeyCallback(window_, &CameraControl::cb_keyboard);
}

bool CameraControl::perturb_active() const
{
  return pert_ != nullptr && pert_->active != 0;
}

CameraControl * CameraControl::from(GLFWwindow * window)
{
  return window ? static_cast<CameraControl *>(glfwGetWindowUserPointer(window)) : nullptr;
}

void CameraControl::cb_mouse_button(GLFWwindow * window, int button, int act, int mods)
{
  if (auto * self = from(window)) {
    self->on_mouse_button(button, act, mods);
  }
}

void CameraControl::cb_mouse_move(GLFWwindow * window, double xpos, double ypos)
{
  if (auto * self = from(window)) {
    self->on_mouse_move(xpos, ypos);
  }
}

void CameraControl::cb_scroll(GLFWwindow * window, double xoffset, double yoffset)
{
  if (auto * self = from(window)) {
    self->on_scroll(xoffset, yoffset);
  }
}

void CameraControl::cb_keyboard(GLFWwindow * window, int key, int scancode, int act, int mods)
{
  if (auto * self = from(window)) {
    self->on_keyboard(key, scancode, act, mods);
  }
}

bool CameraControl::ctrl_down() const
{
  return window_ &&
         ((glfwGetKey(window_, GLFW_KEY_LEFT_CONTROL) == GLFW_PRESS) ||
         (glfwGetKey(window_, GLFW_KEY_RIGHT_CONTROL) == GLFW_PRESS));
}

bool CameraControl::shift_down() const
{
  return window_ &&
         ((glfwGetKey(window_, GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS) ||
         (glfwGetKey(window_, GLFW_KEY_RIGHT_SHIFT) == GLFW_PRESS));
}

void CameraControl::select_body_at_cursor()
{
  if (!model_ || !data_ || !opt_ || !scene_ || !pert_ || !window_) {
    return;
  }

  int width = 0;
  int height = 0;
  glfwGetWindowSize(window_, &width, &height);
  if (width <= 0 || height <= 0) {
    return;
  }

  double xpos = 0.0;
  double ypos = 0.0;
  glfwGetCursorPos(window_, &xpos, &ypos);

  // mjv_select expects OpenGL-style coords with origin at bottom-left.
  const mjtNum aspect = static_cast<mjtNum>(width) / static_cast<mjtNum>(height);
  const mjtNum relx = static_cast<mjtNum>(xpos / static_cast<double>(width));
  const mjtNum rely =
    static_cast<mjtNum>((static_cast<double>(height) - ypos) / static_cast<double>(height));

  mjtNum selpnt[3] = {0, 0, 0};
  int geomid = -1;
  int flexid = -1;
  int skinid = -1;
  const int selbody = mjv_select(
    model_, data_, opt_, aspect, relx, rely, scene_, selpnt, &geomid, &flexid, &skinid);

  if (selbody >= 0) {
    pert_->select = selbody;
    pert_->flexselect = flexid;
    pert_->skinselect = skinid;

    mjtNum tmp[3];
    mju_sub3(tmp, selpnt, data_->xpos + 3 * pert_->select);
    mju_mulMatTVec(pert_->localpos, data_->xmat + 9 * pert_->select, tmp, 3, 3);
  } else {
    pert_->select = 0;
    pert_->flexselect = -1;
    pert_->skinselect = -1;
  }
  pert_->active = 0;
}

void CameraControl::on_mouse_button(int button, int act, int /*mods*/)
{
  if (!window_) {
    return;
  }

  button_left_ = (glfwGetMouseButton(window_, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS);
  button_middle_ = (glfwGetMouseButton(window_, GLFW_MOUSE_BUTTON_MIDDLE) == GLFW_PRESS);
  button_right_ = (glfwGetMouseButton(window_, GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS);

  glfwGetCursorPos(window_, &lastx_, &lasty_);

  // Release: stop any active perturbation.
  if (act == GLFW_RELEASE && pert_) {
    if (mj_mutex_) {
      std::lock_guard<std::mutex> lk(*mj_mutex_);
      pert_->active = 0;
    } else {
      pert_->active = 0;
    }
  }

  if (act != GLFW_PRESS) {
    return;
  }

  // Double-click left: select body under cursor (simulate.cc "Select").
  const double now = glfwGetTime();
  const bool is_double_click =
    (button == last_click_button_) && ((now - last_click_time_) < kDoubleClickSec);
  last_click_time_ = now;
  last_click_button_ = button;

  if (is_double_click && button == GLFW_MOUSE_BUTTON_LEFT) {
    if (mj_mutex_) {
      std::lock_guard<std::mutex> lk(*mj_mutex_);
      select_body_at_cursor();
    } else {
      select_body_at_cursor();
    }
    return;
  }

  // Ctrl + press with a selected body: start translate/rotate perturbation.
  if (!pert_ || !model_ || !data_ || !scene_ || !ctrl_down() || pert_->select <= 0) {
    return;
  }

  int newperturb = 0;
  if (button == GLFW_MOUSE_BUTTON_RIGHT) {
    newperturb = mjPERT_TRANSLATE;  // pull / push
  } else if (button == GLFW_MOUSE_BUTTON_LEFT) {
    newperturb = mjPERT_ROTATE;
  }
  if (newperturb == 0) {
    return;
  }

  auto start_pert = [&]() {
    if (!pert_->active) {
      mjv_initPerturb(model_, data_, scene_, pert_);
      pert_->active = newperturb;
    }
  };
  if (mj_mutex_) {
    std::lock_guard<std::mutex> lk(*mj_mutex_);
    start_pert();
  } else {
    start_pert();
  }
}

void CameraControl::on_mouse_move(double xpos, double ypos)
{
  if (!model_ || !camera_ || !mjv_moveCamera_) {
    return;
  }

  if (!button_left_ && !button_middle_ && !button_right_) {
    return;
  }

  const double dx = xpos - lastx_;
  const double dy = ypos - lasty_;
  lastx_ = xpos;
  lasty_ = ypos;

  int width = 0;
  int height = 0;
  glfwGetWindowSize(window_, &width, &height);
  height = std::max(1, height);

  const bool mod_shift = shift_down();

  int action;
  if (button_right_) {
    action = mod_shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V;
  } else if (button_left_) {
    action = mod_shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V;
  } else {
    action = mjMOUSE_ZOOM;
  }

  const mjtNum reldx = static_cast<mjtNum>(dx / height);
  const mjtNum reldy = static_cast<mjtNum>(dy / height);

  auto move = [&]() {
    if (pert_ && pert_->active && data_ && scene_) {
      // Ctrl-drag moves the selected body (force/torque via applyPerturbForce).
      mjv_movePerturb(model_, data_, action, reldx, reldy, scene_, pert_);
    } else {
      mjv_moveCamera_(model_, action, reldx, reldy, camera_);
      camera_->type = mjCAMERA_FREE;
    }
  };

  if (mj_mutex_) {
    std::lock_guard<std::mutex> lk(*mj_mutex_);
    move();
  } else {
    move();
  }
}

void CameraControl::on_scroll(double /*xoffset*/, double yoffset)
{
  if (!model_ || !camera_ || !mjv_moveCamera_) {
    return;
  }

  if (mj_mutex_) {
    std::lock_guard<std::mutex> lk(*mj_mutex_);
    mjv_moveCamera_(model_, mjMOUSE_ZOOM, 0.0, -0.05 * yoffset, camera_);
    camera_->type = mjCAMERA_FREE;
  } else {
    mjv_moveCamera_(model_, mjMOUSE_ZOOM, 0.0, -0.05 * yoffset, camera_);
    camera_->type = mjCAMERA_FREE;
  }
}

void CameraControl::toggle_adhesion()
{
  if (!model_ || !model_->geom_adhesion) {
    return;
  }

  // Cache original nonzero adhesion values once.
  if (!adhesion_cache_ready_) {
    adhesion_cache_.clear();
    adhesion_cache_.reserve(static_cast<size_t>(model_->ngeom));
    for (int i = 0; i < model_->ngeom; ++i) {
      if (model_->geom_adhesion[i] != 0) {
        adhesion_cache_.emplace_back(i, model_->geom_adhesion[i]);
      }
    }
    adhesion_cache_ready_ = true;
  }

  adhesion_enabled_ = !adhesion_enabled_;
  for (const auto & entry : adhesion_cache_) {
    model_->geom_adhesion[entry.first] = adhesion_enabled_ ? entry.second : 0;
  }

  if (on_adhesion_toggled_) {
    on_adhesion_toggled_(adhesion_enabled_);
  }
}

void CameraControl::on_keyboard(int key, int /*scancode*/, int act, int /*mods*/)
{
  if (act != GLFW_PRESS) {
    return;
  }

  // Backspace: reset camera to MuJoCo defaults (free camera).
  if (key == GLFW_KEY_BACKSPACE && mjv_defaultCamera_ && camera_) {
    if (mj_mutex_) {
      std::lock_guard<std::mutex> lk(*mj_mutex_);
      mjv_defaultCamera_(camera_);
      camera_->type = mjCAMERA_FREE;
    } else {
      mjv_defaultCamera_(camera_);
      camera_->type = mjCAMERA_FREE;
    }
  }

  // Esc: clear body selection / perturbation.
  if (key == GLFW_KEY_ESCAPE && pert_) {
    if (mj_mutex_) {
      std::lock_guard<std::mutex> lk(*mj_mutex_);
      pert_->active = 0;
      pert_->select = 0;
      pert_->flexselect = -1;
      pert_->skinselect = -1;
    } else {
      pert_->active = 0;
      pert_->select = 0;
      pert_->flexselect = -1;
      pert_->skinselect = -1;
    }
  }

  // A: toggle sticky adhesion on all adhesive geoms (palm sticky + object).
  if (key == GLFW_KEY_A) {
    if (mj_mutex_) {
      std::lock_guard<std::mutex> lk(*mj_mutex_);
      toggle_adhesion();
    } else {
      toggle_adhesion();
    }
  }
}

}  // namespace xela_sparshskin_sim
