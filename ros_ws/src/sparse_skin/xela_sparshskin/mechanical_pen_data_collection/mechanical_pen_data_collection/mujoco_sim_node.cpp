// MuJoCo simulation of the LEAP/Xela hand (xela_description/mjcf/scene.xml).
//
// Subscribes to a sim-frame JointState command topic (default: leap_state_sim, published by
// conversions/convert_hardware_to_sim), writes the positions into the matching position
// actuators, steps the physics in real time, and publishes the simulated joint states.
// Contacts between different fingers (bodies under th_ / if_ / mf_ / rf_) are collected after
// every physics step and published on `contact_topic` (std_msgs/String JSON) at the state rate:
//   {"contact": bool, "pairs": [{"fingers": ["if", "mf"], "bodies": ["if_ds", "mf_ds"],
//                                "depth": max penetration (m)}, ...]}
// covering every step since the previous message, so brief touches are not missed.
// With `viewer:=true` a GLFW window renders the scene (left drag: rotate, right drag: move,
// scroll: zoom, double click: select body, backspace: reset, space: pause).

#include <GLFW/glfw3.h>
#include <mujoco/mujoco.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <utility>
#include <thread>
#include <unordered_map>
#include <vector>

#include "ament_index_cpp/get_package_share_directory.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "std_msgs/msg/string.hpp"

namespace
{

using Clock = std::chrono::steady_clock;

// Body name prefixes of the fingers, in leap_state order.
constexpr const char * kFingers[] = {"th", "if", "mf", "rf"};
constexpr int kNumFingers = 4;

// Finger index of a body named "<finger>_...", or -1.
int fingerOfName(const char * name)
{
  if (!name) {return -1;}
  for (int f = 0; f < kNumFingers; ++f) {
    const std::string prefix = std::string(kFingers[f]) + "_";
    if (std::string(name).rfind(prefix, 0) == 0) {return f;}
  }
  return -1;
}

std::string defaultModelPath()
{
  return ament_index_cpp::get_package_share_directory("xela_description") + "/mjcf/scene.xml";
}

}  // namespace

class MujocoSimNode : public rclcpp::Node
{
public:
  MujocoSimNode()
  : Node("mujoco_sim_node")
  {
    model_path_ = declare_parameter<std::string>("model_path", defaultModelPath());
    const auto cmd_topic = declare_parameter<std::string>("cmd_topic", "leap_state_sim");
    const auto state_topic = declare_parameter<std::string>("state_topic", "leap_state_mujoco");
    const auto contact_topic = declare_parameter<std::string>("contact_topic", "finger_contacts");
    const double publish_rate = declare_parameter<double>("publish_rate", 100.0);
    viewer_ = declare_parameter<bool>("viewer", true);
    real_time_factor_ = declare_parameter<double>("real_time_factor", 1.0);

    loadModel();

    state_pub_ = create_publisher<sensor_msgs::msg::JointState>(state_topic, 10);
    if (!contact_topic.empty()) {
      contact_pub_ = create_publisher<std_msgs::msg::String>(contact_topic, 10);
    }
    if (!cmd_topic.empty()) {
      cmd_sub_ = create_subscription<sensor_msgs::msg::JointState>(
        cmd_topic, 10,
        [this](const sensor_msgs::msg::JointState::SharedPtr msg) {onCommand(*msg);});
    }
    if (publish_rate > 0.0) {
      state_timer_ = create_wall_timer(
        std::chrono::duration<double>(1.0 / publish_rate), [this]() {publishState();});
    }

    RCLCPP_INFO(
      get_logger(), "Loaded %s (nq=%ld, nu=%ld, timestep=%.4f s); commands '%s' -> state '%s'",
      model_path_.c_str(), static_cast<long>(m_->nq), static_cast<long>(m_->nu), m_->opt.timestep, cmd_topic.c_str(),
      state_topic.c_str());
    RCLCPP_INFO(
      get_logger(), "Finger-finger contacts on '%s'; viewer window %s",
      contact_topic.empty() ? "(off)" : contact_topic.c_str(),
      viewer_ ? "on" : "off (viewer:=false, headless)");
  }

  ~MujocoSimNode() override
  {
    if (d_) {mj_deleteData(d_);}
    if (m_) {mj_deleteModel(m_);}
  }

  bool viewerEnabled() const {return viewer_;}
  mjModel * model() {return m_;}
  mjData * data() {return d_;}
  std::mutex & mutex() {return mutex_;}

  void reset()
  {
    std::lock_guard<std::mutex> lock(mutex_);
    resetLocked();
  }

  // Advance the simulation until sim time catches up with (scaled) wall time.
  void stepToWallTime()
  {
    const auto now = Clock::now();
    std::lock_guard<std::mutex> lock(mutex_);
    if (paused_) {
      wall_start_ = now;
      sim_start_ = d_->time;
      return;
    }
    const double target =
      sim_start_ + real_time_factor_ * std::chrono::duration<double>(now - wall_start_).count();
    // Resync instead of spiralling when the sim falls far behind (e.g. window dragged).
    if (target - d_->time > 0.1) {
      wall_start_ = now;
      sim_start_ = d_->time;
      mj_step(m_, d_);
      collectFingerContactsLocked();
      return;
    }
    while (d_->time < target) {
      mj_step(m_, d_);
      collectFingerContactsLocked();
    }
  }

  void togglePause()
  {
    std::lock_guard<std::mutex> lock(mutex_);
    paused_ = !paused_;
  }

private:
  void loadModel()
  {
    char error[1000] = "";
    m_ = mj_loadXML(model_path_.c_str(), nullptr, error, sizeof(error));
    if (!m_) {
      throw std::runtime_error("Failed to load MuJoCo model '" + model_path_ + "': " + error);
    }
    d_ = mj_makeData(m_);

    // Map joint name -> actuator id for actuators driving a single joint.
    for (int i = 0; i < m_->nu; ++i) {
      if (m_->actuator_trntype[i] != mjTRN_JOINT) {continue;}
      const char * jname = mj_id2name(m_, mjOBJ_JOINT, m_->actuator_trnid[2 * i]);
      if (jname) {actuator_by_joint_[jname] = i;}
    }
    // Finger of every body: that of its nearest ancestor (or itself) named "<finger>_...".
    body_finger_.assign(m_->nbody, -1);
    for (int b = 1; b < m_->nbody; ++b) {
      for (int a = b; a > 0 && body_finger_[b] < 0; a = m_->body_parentid[a]) {
        body_finger_[b] = fingerOfName(mj_id2name(m_, mjOBJ_BODY, a));
      }
    }
    // Published joints: every hinge / slide joint.
    for (int j = 0; j < m_->njnt; ++j) {
      const int type = m_->jnt_type[j];
      if (type != mjJNT_HINGE && type != mjJNT_SLIDE) {continue;}
      const char * jname = mj_id2name(m_, mjOBJ_JOINT, j);
      if (!jname) {continue;}
      joint_names_.emplace_back(jname);
      joint_qpos_adr_.push_back(m_->jnt_qposadr[j]);
      joint_dof_adr_.push_back(m_->jnt_dofadr[j]);
    }
    resetLocked();
  }

  void resetLocked()
  {
    mj_resetData(m_, d_);
    if (m_->nkey > 0) {mj_resetDataKeyframe(m_, d_, 0);}
    mj_forward(m_, d_);
    wall_start_ = Clock::now();
    sim_start_ = d_->time;
  }

  void onCommand(const sensor_msgs::msg::JointState & msg)
  {
    const size_t n = std::min(msg.name.size(), msg.position.size());
    std::lock_guard<std::mutex> lock(mutex_);
    for (size_t i = 0; i < n; ++i) {
      const auto it = actuator_by_joint_.find(msg.name[i]);
      if (it == actuator_by_joint_.end()) {
        if (warned_unknown_.emplace(msg.name[i], true).second) {
          RCLCPP_WARN(get_logger(), "No actuator for joint '%s'; ignoring", msg.name[i].c_str());
        }
        continue;
      }
      const int a = it->second;
      double ctrl = msg.position[i];
      if (m_->actuator_ctrllimited[a]) {
        ctrl = std::clamp(ctrl, m_->actuator_ctrlrange[2 * a], m_->actuator_ctrlrange[2 * a + 1]);
      }
      d_->ctrl[a] = ctrl;
    }
  }

  // Records the contacts of the current step between bodies of two different fingers.
  void collectFingerContactsLocked()
  {
    for (int i = 0; i < d_->ncon; ++i) {
      const mjContact & c = d_->contact[i];
      if (c.exclude != 0 || c.geom[0] < 0 || c.geom[1] < 0) {continue;}
      int b1 = m_->geom_bodyid[c.geom[0]];
      int b2 = m_->geom_bodyid[c.geom[1]];
      int f1 = body_finger_[b1];
      int f2 = body_finger_[b2];
      if (f1 < 0 || f2 < 0 || f1 == f2) {continue;}
      if (f1 > f2) {
        std::swap(f1, f2);
        std::swap(b1, b2);
      }
      const double depth = std::max(0.0, -static_cast<double>(c.dist));
      auto it = touched_.find({f1, f2});
      if (it == touched_.end()) {
        touched_[{f1, f2}] = {b1, b2, depth};
      } else if (depth > it->second.depth) {
        it->second = {b1, b2, depth};
      }
    }
  }

  // Publishes the finger pairs that touched since the last message, then forgets them.
  void publishContacts()
  {
    std::string json = "{\"contact\": ";
    {
      std::lock_guard<std::mutex> lock(mutex_);
      if (paused_) {collectFingerContactsLocked();}  // no steps while paused
      json += touched_.empty() ? "false" : "true";
      json += ", \"pairs\": [";
      bool first = true;
      for (const auto & [fingers, touch] : touched_) {
        char depth[32];
        std::snprintf(depth, sizeof(depth), "%.6f", touch.depth);
        json += std::string(first ? "" : ", ") + "{\"fingers\": [\"" + kFingers[fingers.first] +
          "\", \"" + kFingers[fingers.second] + "\"], \"bodies\": [\"" +
          mj_id2name(m_, mjOBJ_BODY, touch.body1) + "\", \"" +
          mj_id2name(m_, mjOBJ_BODY, touch.body2) + "\"], \"depth\": " + depth + "}";
        first = false;
      }
      touched_.clear();
    }
    json += "]}";
    std_msgs::msg::String msg;
    msg.data = json;
    contact_pub_->publish(msg);
  }

  void publishState()
  {
    sensor_msgs::msg::JointState msg;
    msg.header.stamp = now();
    msg.name = joint_names_;
    msg.position.resize(joint_names_.size());
    msg.velocity.resize(joint_names_.size());
    msg.effort.resize(joint_names_.size());
    {
      std::lock_guard<std::mutex> lock(mutex_);
      for (size_t i = 0; i < joint_names_.size(); ++i) {
        msg.position[i] = d_->qpos[joint_qpos_adr_[i]];
        msg.velocity[i] = d_->qvel[joint_dof_adr_[i]];
        msg.effort[i] = d_->qfrc_actuator[joint_dof_adr_[i]];
      }
    }
    state_pub_->publish(msg);
    if (contact_pub_) {publishContacts();}
  }

  std::string model_path_;
  bool viewer_{true};
  double real_time_factor_{1.0};
  bool paused_{false};

  mjModel * m_{nullptr};
  mjData * d_{nullptr};
  std::mutex mutex_;
  Clock::time_point wall_start_;
  double sim_start_{0.0};

  struct FingerTouch
  {
    int body1;  // body of the first finger (lower index in kFingers)
    int body2;
    double depth;  // deepest penetration seen (m)
  };
  std::vector<int> body_finger_;  // finger index of each body, -1 if it is not on a finger
  std::map<std::pair<int, int>, FingerTouch> touched_;  // finger pairs touched since last publish

  std::unordered_map<std::string, int> actuator_by_joint_;
  std::unordered_map<std::string, bool> warned_unknown_;
  std::vector<std::string> joint_names_;
  std::vector<int> joint_qpos_adr_;
  std::vector<int> joint_dof_adr_;

  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr state_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr contact_pub_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr cmd_sub_;
  rclcpp::TimerBase::SharedPtr state_timer_;
};

// ---------------------------------------------------------------------------------------------
// GLFW viewer (mouse handling follows MuJoCo's sample/basic.cc)

namespace
{

struct Viewer
{
  MujocoSimNode * node{nullptr};
  mjvCamera cam;
  mjvOption opt;
  mjvScene scn;
  mjvPerturb pert;
  mjrContext con;
  bool button_left{false};
  bool button_middle{false};
  bool button_right{false};
  double lastx{0.0};
  double lasty{0.0};
  double last_click{0.0};
};

Viewer g_viewer;

void keyboard(GLFWwindow *, int key, int, int act, int)
{
  if (act != GLFW_PRESS) {return;}
  if (key == GLFW_KEY_BACKSPACE) {
    g_viewer.node->reset();
  } else if (key == GLFW_KEY_SPACE) {
    g_viewer.node->togglePause();
  }
}

void mouseButton(GLFWwindow * window, int button, int act, int)
{
  g_viewer.button_left = glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS;
  g_viewer.button_middle = glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_MIDDLE) == GLFW_PRESS;
  g_viewer.button_right = glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS;
  glfwGetCursorPos(window, &g_viewer.lastx, &g_viewer.lasty);

  // Double left click: track the selected body (double click on empty space: free camera).
  if (button == GLFW_MOUSE_BUTTON_LEFT && act == GLFW_PRESS) {
    const double t = glfwGetTime();
    if (t - g_viewer.last_click < 0.3) {
      int width, height;
      glfwGetWindowSize(window, &width, &height);
      mjtNum selpnt[3];
      int geomid, flexid, skinid;
      std::lock_guard<std::mutex> lock(g_viewer.node->mutex());
      const int body = mjv_select(
        g_viewer.node->model(), g_viewer.node->data(), &g_viewer.opt,
        static_cast<mjtNum>(width) / height, g_viewer.lastx / width,
        (height - g_viewer.lasty) / height, &g_viewer.scn, selpnt, &geomid, &flexid, &skinid);
      if (body > 0) {
        g_viewer.cam.type = mjCAMERA_TRACKING;
        g_viewer.cam.trackbodyid = body;
        g_viewer.cam.fixedcamid = -1;
      } else {
        g_viewer.cam.type = mjCAMERA_FREE;
      }
    }
    g_viewer.last_click = t;
  }
}

void mouseMove(GLFWwindow * window, double xpos, double ypos)
{
  if (!g_viewer.button_left && !g_viewer.button_middle && !g_viewer.button_right) {return;}
  const double dx = xpos - g_viewer.lastx;
  const double dy = ypos - g_viewer.lasty;
  g_viewer.lastx = xpos;
  g_viewer.lasty = ypos;

  int width, height;
  glfwGetWindowSize(window, &width, &height);
  const bool shift = glfwGetKey(window, GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS ||
    glfwGetKey(window, GLFW_KEY_RIGHT_SHIFT) == GLFW_PRESS;

  mjtMouse action;
  if (g_viewer.button_right) {
    action = shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V;
  } else if (g_viewer.button_left) {
    action = shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V;
  } else {
    action = mjMOUSE_ZOOM;
  }
  std::lock_guard<std::mutex> lock(g_viewer.node->mutex());
  mjv_moveCamera(
    g_viewer.node->model(), action, dx / height, dy / height, &g_viewer.cam);
}

void scroll(GLFWwindow *, double, double yoffset)
{
  std::lock_guard<std::mutex> lock(g_viewer.node->mutex());
  mjv_moveCamera(
    g_viewer.node->model(), mjMOUSE_ZOOM, 0, -0.05 * yoffset, &g_viewer.cam);
}

void runViewer(MujocoSimNode & node)
{
  if (!glfwInit()) {
    throw std::runtime_error("Could not initialize GLFW (no display? run with viewer:=false)");
  }
  GLFWwindow * window = glfwCreateWindow(1200, 900, "MuJoCo: LEAP Xela", nullptr, nullptr);
  if (!window) {
    glfwTerminate();
    throw std::runtime_error("Could not create GLFW window (run with viewer:=false)");
  }
  glfwMakeContextCurrent(window);
  glfwSwapInterval(1);

  mjModel * m = node.model();
  g_viewer.node = &node;
  mjv_defaultCamera(&g_viewer.cam);
  mjv_defaultOption(&g_viewer.opt);
  mjv_defaultScene(&g_viewer.scn);
  mjv_defaultPerturb(&g_viewer.pert);
  mjr_defaultContext(&g_viewer.con);
  mjv_makeScene(m, &g_viewer.scn, 2000);
  mjr_makeContext(m, &g_viewer.con, mjFONTSCALE_150);

  // Start from the model's <visual><global azimuth/elevation> and <statistic> framing.
  g_viewer.cam.azimuth = m->vis.global.azimuth;
  g_viewer.cam.elevation = m->vis.global.elevation;
  g_viewer.cam.distance = 1.5 * m->stat.extent;
  mju_copy3(g_viewer.cam.lookat, m->stat.center);

  glfwSetKeyCallback(window, keyboard);
  glfwSetCursorPosCallback(window, mouseMove);
  glfwSetMouseButtonCallback(window, mouseButton);
  glfwSetScrollCallback(window, scroll);

  while (rclcpp::ok() && !glfwWindowShouldClose(window)) {
    node.stepToWallTime();

    mjrRect viewport = {0, 0, 0, 0};
    glfwGetFramebufferSize(window, &viewport.width, &viewport.height);
    {
      std::lock_guard<std::mutex> lock(node.mutex());
      mjv_updateScene(
        m, node.data(), &g_viewer.opt, &g_viewer.pert, &g_viewer.cam, mjCAT_ALL, &g_viewer.scn);
    }
    mjr_render(viewport, &g_viewer.scn, &g_viewer.con);
    glfwSwapBuffers(window);  // vsync paces the loop
    glfwPollEvents();
  }

  mjv_freeScene(&g_viewer.scn);
  mjr_freeContext(&g_viewer.con);
  glfwDestroyWindow(window);
  glfwTerminate();
}

void runHeadless(MujocoSimNode & node)
{
  const auto period = std::chrono::duration<double>(node.model()->opt.timestep);
  while (rclcpp::ok()) {
    node.stepToWallTime();
    std::this_thread::sleep_for(period);
  }
}

}  // namespace

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int ret = 0;
  try {
    auto node = std::make_shared<MujocoSimNode>();

    // ROS callbacks in the background; physics (and GLFW, which needs the main thread) here.
    rclcpp::executors::MultiThreadedExecutor executor;
    executor.add_node(node);
    std::thread spin_thread([&executor]() {executor.spin();});

    if (node->viewerEnabled()) {
      runViewer(*node);
    } else {
      runHeadless(*node);
    }

    executor.cancel();
    spin_thread.join();
  } catch (const std::exception & e) {
    RCLCPP_FATAL(rclcpp::get_logger("mujoco_sim_node"), "%s", e.what());
    ret = 1;
  }
  if (rclcpp::ok()) {rclcpp::shutdown();}
  return ret;
}
