// ROS 2
#include <rclcpp/rclcpp.hpp>

// msgs
#include <sensor_msgs/msg/joint_state.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <xela_point_cloud_representation/msg/hand_sensors.hpp>
#include <xela_point_cloud_representation/msg/texel.hpp>

// ament
#include <ament_index_cpp/get_package_share_directory.hpp>

// MuJoCo
#include <mujoco/mujoco.h>

#include <algorithm>
#include <array>

#include <cmath>
#include <cstdio>
#include <dlfcn.h>
#include <filesystem>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <vector>
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

    // Subscribe to per-texel sensor values that include the MuJoCo joint names
    // controlling each texel patch (see `sensor_joints.json`).
    const std::string sensor_topic = declare_parameter<std::string>("sensor_topic", "sensor_values");
    sensor_sub_ = create_subscription<xela_point_cloud_representation::msg::HandSensors>(
      sensor_topic, rclcpp::QoS(10),
      [this](xela_point_cloud_representation::msg::HandSensors::ConstSharedPtr msg) { this->on_sensors(std::move(msg)); });

    touch_point_cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>("hand_touch_point_cloud", rclcpp::QoS(10));

    // Initialize derived quantities so the first frame renders a consistent pose.
    {
      std::lock_guard<std::mutex> lk(mj_mutex_);
      api_.mj_forward(model_, data_);
    }

  }

  ~ProcessHandSensorsIntoPointcloudNode() override
  {
    // shutdown_rendering();

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
  struct BodyWorldPose
  {
    int joint_id{-1};
    int body_id{-1};
    std::string body_name;
    std::array<double, 3> pos{0.0, 0.0, 0.0};
    std::array<double, 4> quat{1.0, 0.0, 0.0, 0.0};  // (w,x,y,z) in MuJoCo convention
  };

  std::optional<BodyWorldPose> get_body_world_pose_from_texel_joint_locked(const std::string & joint_name) const
  {
    if (!model_ || !data_ || joint_name.empty()) {
      return std::nullopt;
    }

    const int jid = api_.mj_name2id(model_, mjOBJ_JOINT, joint_name.c_str());
    if (jid < 0 || jid >= model_->njnt) {
      return std::nullopt;
    }

    const int body_id = model_->jnt_bodyid[jid];
    if (body_id < 0 || body_id >= model_->nbody) {
      return std::nullopt;
    }

    BodyWorldPose out;
    out.joint_id = jid;
    out.body_id = body_id;
    if (const char * bname = api_.mj_id2name(model_, mjOBJ_BODY, body_id)) {
      out.body_name = bname;
    }

    const mjtNum * p = &data_->xpos[3 * body_id];
    out.pos = {static_cast<double>(p[0]), static_cast<double>(p[1]), static_cast<double>(p[2])};

    const mjtNum * q = &data_->xquat[4 * body_id];
    out.quat = {static_cast<double>(q[0]), static_cast<double>(q[1]), static_cast<double>(q[2]), static_cast<double>(q[3])};
    RCLCPP_DEBUG(
      get_logger(),
      "texel_joint='%s' -> body='%s' (jid=%d body_id=%d) pos=[%.6f %.6f %.6f] quat(wxyz)=[%.6f %.6f %.6f %.6f]",
      joint_name.c_str(),
      out.body_name.empty() ? "<unnamed>" : out.body_name.c_str(),
      out.joint_id, out.body_id,
      out.pos[0], out.pos[1], out.pos[2],
      out.quat[0], out.quat[1], out.quat[2], out.quat[3]);
    return out;
  }

  void publish_touch_point_cloud_locked()
  {
    if (!touch_point_cloud_pub_) {
      return;
    }

    sensor_msgs::msg::PointCloud2 msg;
    msg.header.stamp = now();
    msg.header.frame_id = "world";

    sensor_msgs::PointCloud2Modifier mod(msg);
    mod.setPointCloud2FieldsByString(1, "xyz");
    mod.resize(latest_body_pose_by_body_name_.size());

    sensor_msgs::PointCloud2Iterator<float> iter_x(msg, "x");
    sensor_msgs::PointCloud2Iterator<float> iter_y(msg, "y");
    sensor_msgs::PointCloud2Iterator<float> iter_z(msg, "z");

    for (const auto & kv : latest_body_pose_by_body_name_) {
      const auto & p = kv.second.pos;
      RCLCPP_DEBUG(
        get_logger(),
        "publishing body='%s' pos=[%.6f %.6f %.6f]",
        kv.second.body_name.empty() ? "<unnamed>" : kv.second.body_name.c_str(),
        p[0], p[1], p[2]);
      *iter_x = static_cast<float>(p[0]);
      *iter_y = static_cast<float>(p[1]);
      *iter_z = static_cast<float>(p[2]);
      ++iter_x;
      ++iter_y;
      ++iter_z;
    }

    touch_point_cloud_pub_->publish(std::move(msg));
  }

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

  // void on_joint_state(sensor_msgs::msg::JointState::ConstSharedPtr msg)
  // {
  //   if (!msg || msg->name.empty() || msg->position.empty() || !data_) {
  //     return;
  //   }
  //   const size_t n = std::min(msg->name.size(), msg->position.size());

  //   std::lock_guard<std::mutex> lk(mj_mutex_);
  //   bool updated_any = false;
  //   std::vector<std::string> changed_joints;
  //   changed_joints.reserve(n);
  //   for (size_t i = 0; i < n; ++i) {
  //     const bool changed = set_joint_qpos_locked(msg->name[i], msg->position[i]);
  //     updated_any |= changed;
  //     if (changed) {
  //       changed_joints.push_back(msg->name[i]);
  //     }
  //   }

  //   if (updated_any) {
  //     api_.mj_forward(model_, data_);

  //     std::sort(changed_joints.begin(), changed_joints.end());
  //     changed_joints.erase(std::unique(changed_joints.begin(), changed_joints.end()), changed_joints.end());
  //     for (const auto & jname : changed_joints) {
  //       if (auto pose = get_body_world_pose_from_texel_joint_locked(jname)) {
  //         const std::string key = !pose->body_name.empty() ? pose->body_name : jname;
  //         latest_body_pose_by_body_name_[key] = *pose;
  //       }
  //     }
  //     publish_touch_point_cloud_locked();
  //   }
  // }
  void on_joint_state(sensor_msgs::msg::JointState::ConstSharedPtr msg)
  {
    if (!msg || msg->name.empty() || msg->position.empty() || !data_) {
      return;
    }

    const size_t n = std::min(msg->name.size(), msg->position.size());

    std::lock_guard<std::mutex> lk(mj_mutex_);

    bool updated_any = false;

    for (size_t i = 0; i < n; ++i) {
      const bool changed =
        set_joint_qpos_locked(msg->name[i], msg->position[i]);

      updated_any |= changed;
    }

    // IMPORTANT:
    // Joint states should ONLY update the hand articulation.
    // Do NOT accumulate bodies into the tactile point cloud here.
    //
    // The tactile point cloud must only be generated from taxel
    // sensor joints inside on_sensors().
    if (updated_any) {
      api_.mj_forward(model_, data_);
    }
  }

  void apply_texels_locked(
    const std::vector<xela_point_cloud_representation::msg::Texel> & texels, bool & updated_any,
    std::vector<std::string> & changed_joints)
  {
    for (const auto & texel : texels) {
      if (!texel.joint_x.empty()) {
        const bool changed = set_joint_qpos_locked(texel.joint_x, static_cast<double>(texel.x));
        updated_any |= changed;
        if (changed) {
          changed_joints.push_back(texel.joint_x);
        }
      }
      if (!texel.joint_y.empty()) {
        const bool changed = set_joint_qpos_locked(texel.joint_y, static_cast<double>(texel.y));
        updated_any |= changed;
        if (changed) {
          changed_joints.push_back(texel.joint_y);
        }
      }
      if (!texel.joint_z.empty()) {
        const bool changed = set_joint_qpos_locked(texel.joint_z, static_cast<double>(texel.z));
        updated_any |= changed;
        if (changed) {
          changed_joints.push_back(texel.joint_z);
        }
      }
    }
  }

  void on_sensors(xela_point_cloud_representation::msg::HandSensors::ConstSharedPtr msg)
  {
    if (!msg || !data_) {
      return;
    }

    std::lock_guard<std::mutex> lk(mj_mutex_);
    bool updated_any = false;

    for (const auto & texel : msg->texels) {
      if (!texel.joint_x.empty()) {
        updated_any |= set_joint_qpos_locked(texel.joint_x, static_cast<double>(texel.x));
      }
      if (!texel.joint_y.empty()) {
        updated_any |= set_joint_qpos_locked(texel.joint_y, static_cast<double>(texel.y));
      }
      if (!texel.joint_z.empty()) {
        updated_any |= set_joint_qpos_locked(texel.joint_z, static_cast<double>(texel.z));
      }
    }

    api_.mj_forward(model_, data_);

    latest_body_pose_by_body_name_.clear();

    for (const auto & texel : msg->texels) {
      if (texel.joint_x.empty()) {
        continue;
      }

      if (auto pose = get_body_world_pose_from_texel_joint_locked(texel.joint_x)) {
        const std::string key = !pose->body_name.empty() ? pose->body_name : texel.joint_x;
        latest_body_pose_by_body_name_[key] = *pose;
      } else {
        RCLCPP_WARN_THROTTLE(
          get_logger(),
          *get_clock(),
          2000,
          "Missing pose for taxel joint_x: %s",
          texel.joint_x.c_str());
      }
    }

    publish_touch_point_cloud_locked();
  }

  // void on_sensors(xela_point_cloud_representation::msg::HandSensors::ConstSharedPtr msg)
  // {
  //   if (!msg || !data_) {
  //     return;
  //   }

  //   std::lock_guard<std::mutex> lk(mj_mutex_);
  //   bool updated_any = false;
  //   std::vector<std::string> changed_joints;
  //   changed_joints.reserve(367+16);

  //   apply_texels_locked(msg->texels, updated_any, changed_joints);

  //   if (updated_any) {
  //     latest_body_pose_by_body_name_.clear();
  //     api_.mj_forward(model_, data_);

  //     std::sort(changed_joints.begin(), changed_joints.end());
  //     changed_joints.erase(std::unique(changed_joints.begin(), changed_joints.end()), changed_joints.end());
  //     for (const auto & jname : changed_joints) {
  //       if (auto pose = get_body_world_pose_from_texel_joint_locked(jname)) {
  //         const std::string key = !pose->body_name.empty() ? pose->body_name : jname;
  //         latest_body_pose_by_body_name_[key] = *pose;
  //       }
  //     }
  //     publish_touch_point_cloud_locked();
  //   }
  // }

  bool set_joint_qpos_locked(const std::string & joint_name, double desired_qpos)
  {
    if (!model_ || !data_) {
      return false;
    }
    const auto it = qpos_index_by_joint_name_.find(joint_name);
    if (it == qpos_index_by_joint_name_.end()) {
      return false;
    }

    double v = desired_qpos;
    const int jid = api_.mj_name2id(model_, mjOBJ_JOINT, joint_name.c_str());
    if (jid >= 0) {
      const double lo = model_->jnt_range[jid * 2 + 0];
      const double hi = model_->jnt_range[jid * 2 + 1];
      v = std::clamp(v, lo, hi);
    }

    const double prev = static_cast<double>(data_->qpos[it->second]);
    if (std::isfinite(prev) && std::abs(prev - v) < 1e-12) {
      return false;
    }
    data_->qpos[it->second] = v;
    return true;
  }

  std::string resolve_scene_xml_path()
  {
    //Note to self: The file path is not comming from launch file. This is a fuckup
    const std::string xela_description_share =
      ament_index_cpp::get_package_share_directory("xela_description");
    fs::path scene = fs::path(xela_description_share) / "mjcf" / "scene_touch_point_cloud.xml";

    if (!fs::exists(scene)) {
      throw std::runtime_error("scene_touch_point_cloud.xml not found at: " + scene.string());
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

  MujocoApi api_;
  mjModel * model_{nullptr};
  mjData * data_{nullptr};
  std::mutex mj_mutex_;
  std::unordered_map<std::string, int> qpos_index_by_joint_name_;
  std::unordered_map<std::string, BodyWorldPose> latest_body_pose_by_body_name_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_sub_;
  rclcpp::Subscription<xela_point_cloud_representation::msg::HandSensors>::SharedPtr sensor_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr touch_point_cloud_pub_;

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
