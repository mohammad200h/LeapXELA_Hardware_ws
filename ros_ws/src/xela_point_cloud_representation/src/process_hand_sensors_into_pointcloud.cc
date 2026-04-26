// ROS 2
#include <rclcpp/rclcpp.hpp>

// msgs
#include <sensor_msgs/msg/joint_state.hpp>

// ament
#include <ament_index_cpp/get_package_share_directory.hpp>

// MuJoCo
#include <mujoco/mujoco.h>

#include <GLFW/glfw3.h>

#include <chrono>
#include <cstdio>
#include <dlfcn.h>
#include <filesystem>
#include <mutex>
#include <unordered_map>
#include <memory>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

struct MujocoApi
{
  void * handle{nullptr};

  mjModel * (*mj_loadXML)(const char *, const mjVFS *, char *, int){nullptr};
  mjData * (*mj_makeData)(const mjModel *){nullptr};
  void (*mj_deleteModel)(mjModel *){nullptr};
  void (*mj_deleteData)(mjData *){nullptr};
  void (*mj_forward)(const mjModel *, mjData *){nullptr};
  int (*mj_name2id)(const mjModel *, int, const char *){nullptr};
  const char * (*mj_id2name)(const mjModel *, int, int){nullptr};

  void (*mjv_defaultCamera)(mjvCamera *){nullptr};
  void (*mjv_defaultOption)(mjvOption *){nullptr};
  void (*mjv_defaultScene)(mjvScene *){nullptr};
  void (*mjr_defaultContext)(mjrContext *){nullptr};
  void (*mjv_makeScene)(const mjModel *, mjvScene *, int){nullptr};
  void (*mjr_makeContext)(const mjModel *, mjrContext *, int){nullptr};
  void (*mjv_updateScene)(
    const mjModel *, const mjData *, const mjvOption *, const mjvPerturb *, const mjvCamera *, int, mjvScene *){nullptr};
  void (*mjr_render)(mjrRect, const mjvScene *, const mjrContext *){nullptr};
  void (*mjr_freeContext)(mjrContext *){nullptr};
  void (*mjv_freeScene)(mjvScene *){nullptr};

  static void * open_library()
  {
    // Try common SONAMEs in order.
    const char * candidates[] = {"libmujoco.so", "libmujoco.so.3", "libmujoco.so.3.8.1"};
    for (const char * name : candidates) {
      if (void * h = dlopen(name, RTLD_NOW | RTLD_LOCAL)) {
        return h;
      }
    }
    return nullptr;
  }

  template <typename Fn>
  static Fn load_symbol(void * h, const char * sym)
  {
    dlerror();  // clear
    void * p = dlsym(h, sym);
    const char * err = dlerror();
    if (err != nullptr || p == nullptr) {
      throw std::runtime_error(std::string("Failed to load symbol '") + sym + "': " + (err ? err : ""));
    }
    return reinterpret_cast<Fn>(p);
  }

  void load()
  {
    handle = open_library();
    if (!handle) {
      const char * err = dlerror();
      throw std::runtime_error(std::string("Failed to dlopen MuJoCo library: ") + (err ? err : "(unknown error)"));
    }

    mj_loadXML = load_symbol<decltype(mj_loadXML)>(handle, "mj_loadXML");
    mj_makeData = load_symbol<decltype(mj_makeData)>(handle, "mj_makeData");
    mj_deleteModel = load_symbol<decltype(mj_deleteModel)>(handle, "mj_deleteModel");
    mj_deleteData = load_symbol<decltype(mj_deleteData)>(handle, "mj_deleteData");
    mj_forward = load_symbol<decltype(mj_forward)>(handle, "mj_forward");
    mj_name2id = load_symbol<decltype(mj_name2id)>(handle, "mj_name2id");
    mj_id2name = load_symbol<decltype(mj_id2name)>(handle, "mj_id2name");

    mjv_defaultCamera = load_symbol<decltype(mjv_defaultCamera)>(handle, "mjv_defaultCamera");
    mjv_defaultOption = load_symbol<decltype(mjv_defaultOption)>(handle, "mjv_defaultOption");
    mjv_defaultScene = load_symbol<decltype(mjv_defaultScene)>(handle, "mjv_defaultScene");
    mjr_defaultContext = load_symbol<decltype(mjr_defaultContext)>(handle, "mjr_defaultContext");
    mjv_makeScene = load_symbol<decltype(mjv_makeScene)>(handle, "mjv_makeScene");
    mjr_makeContext = load_symbol<decltype(mjr_makeContext)>(handle, "mjr_makeContext");
    mjv_updateScene = load_symbol<decltype(mjv_updateScene)>(handle, "mjv_updateScene");
    mjr_render = load_symbol<decltype(mjr_render)>(handle, "mjr_render");
    mjr_freeContext = load_symbol<decltype(mjr_freeContext)>(handle, "mjr_freeContext");
    mjv_freeScene = load_symbol<decltype(mjv_freeScene)>(handle, "mjv_freeScene");
  }

  ~MujocoApi()
  {
    if (handle) {
      dlclose(handle);
      handle = nullptr;
    }
  }
};

class ProcessHandSensorsIntoPointcloudNode final : public rclcpp::Node
{
public:
  ProcessHandSensorsIntoPointcloudNode()
  : rclcpp::Node("process_hand_sensors_into_pointcloud")
  {
    api_.load();

    const std::string scene_path = resolve_scene_xml_path();
    RCLCPP_INFO(get_logger(), "Loading MuJoCo MJCF: %s", scene_path.c_str());

    load_mujoco_model(scene_path);
    build_qpos_index_map();

    const std::string joint_topic = declare_parameter<std::string>("joint_topic", "xela_joint_publisher");
    joint_sub_ = create_subscription<sensor_msgs::msg::JointState>(
      joint_topic, rclcpp::QoS(10),
      [this](sensor_msgs::msg::JointState::ConstSharedPtr msg) { this->on_joint_state(std::move(msg)); });

    const int64_t render_hz = declare_parameter<int64_t>("render_hz", 60);
    if (render_hz <= 0) {
      throw std::runtime_error("Parameter 'render_hz' must be > 0");
    }
    render_hz_ = static_cast<double>(render_hz);

    init_rendering();
    // Initialize derived quantities so the first frame renders a consistent pose.
    {
      std::lock_guard<std::mutex> lk(mj_mutex_);
      api_.mj_forward(model_, data_);
    }

    const auto period = std::chrono::duration<double>(1.0 / render_hz_);
    render_timer_ = create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(period),
      [this]() { this->render_once(); });
  }

  ~ProcessHandSensorsIntoPointcloudNode() override
  {
    shutdown_rendering();

    if (data_) {
      api_.mj_deleteData(data_);
      data_ = nullptr;
    }
    if (model_) {
      api_.mj_deleteModel(model_);
      model_ = nullptr;
    }
  }

private:
  void build_qpos_index_map()
  {
    qpos_index_by_joint_name_.clear();
    if (!model_) {
      return;
    }

    // Build mapping from joint name -> qpos address for 1-DoF joints.
    // (This matches how your Python publisher uses MuJoCo joint names.)
    for (int j = 0; j < model_->njnt; ++j) {
      const char * name = api_.mj_id2name(model_, mjOBJ_JOINT, j);
      if (!name) {
        continue;
      }
      qpos_index_by_joint_name_[name] = static_cast<int>(model_->jnt_qposadr[j]);
    }
  }

  void on_joint_state(sensor_msgs::msg::JointState::ConstSharedPtr msg)
  {
    if (!msg || msg->name.empty() || msg->position.empty() || !data_) {
      return;
    }
    const size_t n = std::min(msg->name.size(), msg->position.size());

    std::lock_guard<std::mutex> lk(mj_mutex_);
    bool updated_any = false;
    for (size_t i = 0; i < n; ++i) {
      const auto it = qpos_index_by_joint_name_.find(msg->name[i]);
      if (it == qpos_index_by_joint_name_.end()) {
        continue;
      }

      const int qpos_i = it->second;
      double v = msg->position[i];
      // Clamp to joint range if available (same semantics as Python side).
      // MuJoCo stores joint range in model_->jnt_range for joint index.
      const int jid = api_.mj_name2id(model_, mjOBJ_JOINT, msg->name[i].c_str());
      if (jid >= 0) {
        const double lo = model_->jnt_range[jid * 2 + 0];
        const double hi = model_->jnt_range[jid * 2 + 1];
        if (v < lo) v = lo;
        if (v > hi) v = hi;
      }

      data_->qpos[qpos_i] = v;
      updated_any = true;
    }

    if (updated_any) {
      api_.mj_forward(model_, data_);
    }
  }

  std::string resolve_scene_xml_path()
  {
    const std::string xela_description_share =
      ament_index_cpp::get_package_share_directory("xela_description");
    fs::path scene = fs::path(xela_description_share) / "mjcf" / "scene.xml";

    if (!fs::exists(scene)) {
      throw std::runtime_error("scene.xml not found at: " + scene.string());
    }
    return scene.string();
  }

  void load_mujoco_model(const std::string & scene_path)
  {
    // MuJoCo resolves <include file="..."/> relative to current working directory in some setups.
    // To make includes robust, temporarily set CWD to the directory containing scene.xml.
    const fs::path scene_fs(scene_path);
    const fs::path scene_dir = scene_fs.parent_path();
    const fs::path old_cwd = fs::current_path();

    char err[1024] = {0};
    try {
      fs::current_path(scene_dir);
      model_ = api_.mj_loadXML(scene_path.c_str(), /*vfs=*/nullptr, err, sizeof(err));
      fs::current_path(old_cwd);
    } catch (...) {
      fs::current_path(old_cwd);
      throw;
    }

    if (!model_) {
      throw std::runtime_error(std::string("mj_loadXML failed: ") + err);
    }

    data_ = api_.mj_makeData(model_);
    if (!data_) {
      api_.mj_deleteModel(model_);
      model_ = nullptr;
      throw std::runtime_error("mj_makeData failed");
    }
  }

  void init_rendering()
  {
    if (!glfwInit()) {
      throw std::runtime_error("glfwInit() failed");
    }

    glfwWindowHint(GLFW_VISIBLE, GLFW_TRUE);
    // Force desktop OpenGL (not GLES). Prefer a compatibility profile so that
    // legacy extension queries work across drivers/setups.
    glfwWindowHint(GLFW_CLIENT_API, GLFW_OPENGL_API);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 1);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_ANY_PROFILE);

    window_ = glfwCreateWindow(1200, 900, "MuJoCo Viewer (process_hand_sensors_into_pointcloud)", nullptr, nullptr);
    if (!window_) {
      glfwTerminate();
      throw std::runtime_error("glfwCreateWindow() failed");
    }

    glfwMakeContextCurrent(window_);
    glfwSwapInterval(1);

    // Helpful diagnostics when rendering fails.
    const unsigned char * gl_version = glGetString(GL_VERSION);
    const unsigned char * gl_renderer = glGetString(GL_RENDERER);
    const unsigned char * gl_vendor = glGetString(GL_VENDOR);
    RCLCPP_INFO(
      get_logger(), "OpenGL vendor='%s' renderer='%s' version='%s'",
      gl_vendor ? reinterpret_cast<const char *>(gl_vendor) : "(null)",
      gl_renderer ? reinterpret_cast<const char *>(gl_renderer) : "(null)",
      gl_version ? reinterpret_cast<const char *>(gl_version) : "(null)");
    RCLCPP_INFO(
      get_logger(), "GLFW reports GL_ARB_framebuffer_object: %s",
      glfwExtensionSupported("GL_ARB_framebuffer_object") ? "yes" : "no");

    api_.mjv_defaultCamera(&cam_);
    api_.mjv_defaultOption(&opt_);
    api_.mjv_defaultScene(&scn_);
    api_.mjr_defaultContext(&con_);

    api_.mjv_makeScene(model_, &scn_, 2000);
    api_.mjr_makeContext(model_, &con_, mjFONTSCALE_150);

    cam_.azimuth = 0;
    cam_.elevation = -50.0;
    cam_.distance = 1.0;
  }

  void shutdown_rendering()
  {
    if (window_) {
      api_.mjr_freeContext(&con_);
      api_.mjv_freeScene(&scn_);

      glfwDestroyWindow(window_);
      window_ = nullptr;
      glfwTerminate();
    }
  }

  void render_once()
  {
    if (!window_) {
      return;
    }
    if (glfwWindowShouldClose(window_)) {
      rclcpp::shutdown();
      return;
    }

    {
      std::lock_guard<std::mutex> lk(mj_mutex_);
      // Viewer-only mode: do NOT advance simulation time. Just refresh derived quantities
      // in case external code updated qpos/qvel/ctrl since the last render.
      api_.mj_forward(model_, data_);
    }

    mjrRect viewport{0, 0, 0, 0};
    glfwGetFramebufferSize(window_, &viewport.width, &viewport.height);

    {
      std::lock_guard<std::mutex> lk(mj_mutex_);
      api_.mjv_updateScene(model_, data_, &opt_, /*pert=*/nullptr, &cam_, mjCAT_ALL, &scn_);
      api_.mjr_render(viewport, &scn_, &con_);
    }

    glfwSwapBuffers(window_);
    glfwPollEvents();
  }

  MujocoApi api_;
  mjModel * model_{nullptr};
  mjData * data_{nullptr};
  std::mutex mj_mutex_;
  std::unordered_map<std::string, int> qpos_index_by_joint_name_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_sub_;

  double render_hz_{60.0};
  rclcpp::TimerBase::SharedPtr render_timer_;

  GLFWwindow * window_{nullptr};
  mjvCamera cam_{};
  mjvOption opt_{};
  mjvScene scn_{};
  mjrContext con_{};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    auto node = std::make_shared<ProcessHandSensorsIntoPointcloudNode>();
    rclcpp::spin(node);
  } catch (const std::exception & e) {
    // rclcpp might not be initialized enough for logging if construction fails very early.
    fprintf(stderr, "Fatal error: %s\n", e.what());
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
