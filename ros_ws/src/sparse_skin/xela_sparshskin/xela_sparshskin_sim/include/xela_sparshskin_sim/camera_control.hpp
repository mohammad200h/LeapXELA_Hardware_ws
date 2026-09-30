#pragma once

#include <GLFW/glfw3.h>
#include <mujoco/mujoco.h>

#include <functional>
#include <mutex>
#include <utility>
#include <vector>

namespace xela_sparshskin_sim
{

// MuJoCo simulate.cc-style GLFW interaction:
//   - mouse drag / scroll: free camera
//   - left double-click: select body under cursor
//   - Ctrl + left drag: rotate selected body (torque)
//   - Ctrl + right drag: translate / pull selected body (force)
//   - A: toggle geom adhesion on/off
// Designed to be used with `glfwSetWindowUserPointer(window, this)`.
class CameraControl final
{
public:
  using MoveCameraFn = void (*)(const mjModel *, int, mjtNum, mjtNum, mjvCamera *);
  using DefaultCameraFn = void (*)(mjvCamera *);
  using AdhesionToggledFn = std::function<void(bool enabled)>;

  CameraControl(
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
    AdhesionToggledFn on_adhesion_toggled = nullptr);

  void install();

  // True while a Ctrl-drag perturbation is active.
  bool perturb_active() const;

  bool adhesion_enabled() const { return adhesion_enabled_; }

private:
  static CameraControl * from(GLFWwindow * window);

  static void cb_mouse_button(GLFWwindow * window, int button, int act, int mods);
  static void cb_mouse_move(GLFWwindow * window, double xpos, double ypos);
  static void cb_scroll(GLFWwindow * window, double xoffset, double yoffset);
  static void cb_keyboard(GLFWwindow * window, int key, int scancode, int act, int mods);

  void on_mouse_button(int button, int act, int mods);
  void on_mouse_move(double xpos, double ypos);
  void on_scroll(double xoffset, double yoffset);
  void on_keyboard(int key, int scancode, int act, int mods);

  void select_body_at_cursor();
  void toggle_adhesion();
  bool ctrl_down() const;
  bool shift_down() const;

  GLFWwindow * window_{nullptr};
  mjModel * model_{nullptr};
  mjData * data_{nullptr};
  mjvCamera * camera_{nullptr};
  mjvOption * opt_{nullptr};
  mjvScene * scene_{nullptr};
  mjvPerturb * pert_{nullptr};
  MoveCameraFn mjv_moveCamera_{nullptr};
  DefaultCameraFn mjv_defaultCamera_{nullptr};
  std::mutex * mj_mutex_{nullptr};
  AdhesionToggledFn on_adhesion_toggled_;

  bool button_left_{false};
  bool button_middle_{false};
  bool button_right_{false};
  double lastx_{0.0};
  double lasty_{0.0};

  // Double-click detection for body selection.
  double last_click_time_{0.0};
  int last_click_button_{-1};

  bool adhesion_enabled_{true};
  bool adhesion_cache_ready_{false};
  std::vector<std::pair<int, mjtNum>> adhesion_cache_;
};

}  // namespace xela_sparshskin_sim
