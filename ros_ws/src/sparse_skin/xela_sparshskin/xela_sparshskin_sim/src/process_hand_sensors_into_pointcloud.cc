// ROS 2
#include <rclcpp/rclcpp.hpp>

// msgs
#include <sensor_msgs/msg/joint_state.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <xela_sparshskin_sim/msg/hand_sensors.hpp>
#include <xela_sparshskin_sim/msg/taxel_pertubation.hpp>
#include <xela_sparshskin_sim/msg/texel.hpp>

// ament
#include <ament_index_cpp/get_package_share_directory.hpp>

// MuJoCo
#include <mujoco/mujoco.h>

#include <GLFW/glfw3.h>

#include <xela_sparshskin_sim/camera_control.hpp>
#include <xela_sparshskin_sim/object.hpp>
#include <xela_sparshskin_sim/stickyskin.hpp>

#include <algorithm>
#include <array>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <filesystem>
#include <limits>
#include <mutex>
#include <optional>
#include <sstream>
#include <unordered_map>
#include <utility>
#include <vector>
#include <memory>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace
{

// Minimal JSON subset parser for leap_sensor_taxel_map.json
// (nested objects + arrays of ints + strings).
struct JsonValue
{
  enum class Type { Object, Array, String, Number };
  Type type{Type::Object};
  // Heap-allocate recursive containers so JsonValue is a complete type.
  std::unique_ptr<std::unordered_map<std::string, JsonValue>> object;
  std::unique_ptr<std::vector<JsonValue>> array;
  std::string str;
  int number{0};

  JsonValue() = default;
  JsonValue(JsonValue &&) noexcept = default;
  JsonValue & operator=(JsonValue &&) noexcept = default;
  JsonValue(const JsonValue & other)
  {
    type = other.type;
    str = other.str;
    number = other.number;
    if (other.object) {
      object = std::make_unique<std::unordered_map<std::string, JsonValue>>(*other.object);
    }
    if (other.array) {
      array = std::make_unique<std::vector<JsonValue>>(*other.array);
    }
  }
  JsonValue & operator=(const JsonValue & other)
  {
    if (this == &other) {
      return *this;
    }
    type = other.type;
    str = other.str;
    number = other.number;
    object.reset();
    array.reset();
    if (other.object) {
      object = std::make_unique<std::unordered_map<std::string, JsonValue>>(*other.object);
    }
    if (other.array) {
      array = std::make_unique<std::vector<JsonValue>>(*other.array);
    }
    return *this;
  }
};

class JsonParser
{
public:
  explicit JsonParser(std::string text)
  : text_(std::move(text))
  {
  }

  JsonValue parse()
  {
    skip_ws();
    JsonValue v = parse_value();
    skip_ws();
    if (pos_ != text_.size()) {
      throw std::runtime_error("Trailing junk in JSON at pos " + std::to_string(pos_));
    }
    return v;
  }

private:
  void skip_ws()
  {
    while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) {
      ++pos_;
    }
  }

  char peek() const
  {
    if (pos_ >= text_.size()) {
      throw std::runtime_error("Unexpected end of JSON");
    }
    return text_[pos_];
  }

  char get()
  {
    const char c = peek();
    ++pos_;
    return c;
  }

  void expect(char c)
  {
    if (get() != c) {
      throw std::runtime_error(std::string("Expected '") + c + "' in JSON");
    }
  }

  JsonValue parse_value()
  {
    skip_ws();
    const char c = peek();
    if (c == '{') {
      return parse_object();
    }
    if (c == '[') {
      return parse_array();
    }
    if (c == '"') {
      JsonValue v;
      v.type = JsonValue::Type::String;
      v.str = parse_string();
      return v;
    }
    if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) {
      JsonValue v;
      v.type = JsonValue::Type::Number;
      v.number = parse_number();
      return v;
    }
    throw std::runtime_error(std::string("Unexpected JSON char: ") + c);
  }

  JsonValue parse_object()
  {
    JsonValue v;
    v.type = JsonValue::Type::Object;
    v.object = std::make_unique<std::unordered_map<std::string, JsonValue>>();
    expect('{');
    skip_ws();
    if (peek() == '}') {
      get();
      return v;
    }
    while (true) {
      skip_ws();
      const std::string key = parse_string();
      skip_ws();
      expect(':');
      v.object->emplace(key, parse_value());
      skip_ws();
      const char sep = get();
      if (sep == '}') {
        break;
      }
      if (sep != ',') {
        throw std::runtime_error("Expected ',' or '}' in JSON object");
      }
    }
    return v;
  }

  JsonValue parse_array()
  {
    JsonValue v;
    v.type = JsonValue::Type::Array;
    v.array = std::make_unique<std::vector<JsonValue>>();
    expect('[');
    skip_ws();
    if (peek() == ']') {
      get();
      return v;
    }
    while (true) {
      v.array->push_back(parse_value());
      skip_ws();
      const char sep = get();
      if (sep == ']') {
        break;
      }
      if (sep != ',') {
        throw std::runtime_error("Expected ',' or ']' in JSON array");
      }
    }
    return v;
  }

  std::string parse_string()
  {
    expect('"');
    std::string out;
    while (true) {
      const char c = get();
      if (c == '"') {
        return out;
      }
      if (c == '\\') {
        out.push_back(get());
        continue;
      }
      out.push_back(c);
    }
  }

  int parse_number()
  {
    const size_t start = pos_;
    if (peek() == '-') {
      get();
    }
    while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
      ++pos_;
    }
    return std::stoi(text_.substr(start, pos_ - start));
  }

  std::string text_;
  size_t pos_{0};
};

struct PatchBinding
{
  const char * finger;
  const char * part;
  const char * flex_prefix;
  bool tip_one_based;
  int ncols;  // 0 for tips; pad column count otherwise
};

// Map keys in leap_sensor_taxel_map.json -> MuJoCo flex vertex body prefixes.
// Keep the JSON row/column ordering unchanged so the simulator matches the
// reference taxel layout used elsewhere in the stack.
constexpr PatchBinding kPatchBindings[] = {
  {"TH", "tip", "flex_th_tip", true, 0},
  {"TH", "ds", "flex_th_ds_uspa44", false, 4},
  {"TH", "third", "flex_th_px_uspa44", false, 4},
  {"IF", "tip", "flex_if_tip", true, 0},
  {"IF", "ds", "flex_if_md_uspa44", false, 4},
  {"IF", "md", "flex_if_px_uspa44", false, 4},
  {"IF", "bs", "flex_if_bs_uspa44", false, 4},
  {"MF", "tip", "flex_mf_tip", true, 0},
  {"MF", "ds", "flex_mf_md_uspa44", false, 4},
  {"MF", "md", "flex_mf_px_uspa44", false, 4},
  {"MF", "px", "flex_mf_bs_uspa44", false, 4},
  {"RF", "tip", "flex_rf_tip", true, 0},
  {"RF", "ds", "flex_rf_md_uspa44", false, 4},
  {"RF", "md", "flex_rf_px_uspa44", false, 4},
  {"RF", "bs", "flex_rf_bs_uspa44", false, 4},
  {"Palm", "uspa46_1", "flex_uspa46_1", false, 4},
  {"Palm", "uspa46_2", "flex_uspa46_2", false, 4},
  {"Palm", "uspa46_3", "flex_uspa46_3", false, 4},
};

struct FlexVertexTaxel
{
  std::string sensor_name;
  int32_t taxel_id{-1};
  int flex_id{-1};
  int vert_index{-1};
  int body_id{-1};
};

std::unordered_map<std::string, int32_t> build_flex_vertex_taxel_id_map(const JsonValue & root)
{
  if (root.type != JsonValue::Type::Object || !root.object) {
    throw std::runtime_error("Taxel map root must be a JSON object");
  }

  std::unordered_map<std::string, int32_t> out;
  out.reserve(368);

  for (const PatchBinding & binding : kPatchBindings) {
    const auto finger_it = root.object->find(binding.finger);
    if (finger_it == root.object->end() ||
      finger_it->second.type != JsonValue::Type::Object || !finger_it->second.object)
    {
      throw std::runtime_error(std::string("Missing finger key in taxel map: ") + binding.finger);
    }
    const auto part_it = finger_it->second.object->find(binding.part);
    if (part_it == finger_it->second.object->end() ||
      part_it->second.type != JsonValue::Type::Object || !part_it->second.object)
    {
      throw std::runtime_error(
        std::string("Missing part key in taxel map: ") + binding.finger + "/" + binding.part);
    }

    std::vector<std::pair<int, const JsonValue *>> rows;
    rows.reserve(part_it->second.object->size());
    for (const auto & kv : *part_it->second.object) {
      rows.emplace_back(std::stoi(kv.first), &kv.second);
    }
    std::sort(rows.begin(), rows.end(), [](const auto & a, const auto & b) { return a.first < b.first; });

    if (binding.tip_one_based) {
      int idx = 1;
      for (const auto & row : rows) {
        if (row.second->type != JsonValue::Type::Array || !row.second->array) {
          throw std::runtime_error("Tip taxel map row must be an array");
        }
        for (const JsonValue & cell : *row.second->array) {
          if (cell.type != JsonValue::Type::Number) {
            throw std::runtime_error("Taxel id must be a number");
          }
          out.emplace(std::string(binding.flex_prefix) + "_" + std::to_string(idx), cell.number);
          ++idx;
        }
      }
    } else {
      for (size_t row_idx = 0; row_idx < rows.size(); ++row_idx) {
        const JsonValue & row = *rows[row_idx].second;
        if (row.type != JsonValue::Type::Array || !row.array) {
          throw std::runtime_error("Pad taxel map row must be an array");
        }
        if (static_cast<int>(row.array->size()) != binding.ncols) {
          throw std::runtime_error(
            std::string("Unexpected column count for ") + binding.flex_prefix);
        }
        for (int m = 0; m < binding.ncols; ++m) {
          const JsonValue & cell = (*row.array)[static_cast<size_t>(m)];
          if (cell.type != JsonValue::Type::Number) {
            throw std::runtime_error("Taxel id must be a number");
          }
          const int vertex = static_cast<int>(row_idx) * binding.ncols + m;
          out.emplace(std::string(binding.flex_prefix) + "_" + std::to_string(vertex), cell.number);
        }
      }
    }
  }

  if (out.size() != 368) {
    throw std::runtime_error("Expected 368 flex vertex taxel mappings, got " + std::to_string(out.size()));
  }
  return out;
}

}  // namespace

struct MujocoApi
{
  mjModel * (*mj_loadXML)(const char *, const mjVFS *, char *, int){nullptr};
  mjModel * (*mj_compile)(mjSpec *, const mjVFS *){nullptr};
  void (*mj_deleteSpec)(mjSpec *){nullptr};
  mjData * (*mj_makeData)(const mjModel *){nullptr};
  void (*mj_deleteModel)(mjModel *){nullptr};
  void (*mj_deleteData)(mjData *){nullptr};
  void (*mj_forward)(const mjModel *, mjData *){nullptr};
  void (*mj_step)(const mjModel *, mjData *){nullptr};
  int (*mj_name2id)(const mjModel *, int, const char *){nullptr};
  const char * (*mj_id2name)(const mjModel *, int, int){nullptr};
  void (*mj_contactForce)(const mjModel *, const mjData *, int, mjtNum result[6]){nullptr};

  void (*mjv_defaultCamera)(mjvCamera *){nullptr};
  void (*mjv_defaultOption)(mjvOption *){nullptr};
  void (*mjv_defaultScene)(mjvScene *){nullptr};
  void (*mjv_defaultPerturb)(mjvPerturb *){nullptr};
  void (*mjr_defaultContext)(mjrContext *){nullptr};
  void (*mjv_makeScene)(const mjModel *, mjvScene *, int){nullptr};
  void (*mjr_makeContext)(const mjModel *, mjrContext *, int){nullptr};
  void (*mjv_moveCamera)(const mjModel *, int, mjtNum, mjtNum, mjvCamera *){nullptr};
  void (*mjv_applyPerturbForce)(const mjModel *, mjData *, const mjvPerturb *){nullptr};
  void (*mjv_initGeom)(mjvGeom *, int, const mjtNum[3], const mjtNum[3], const mjtNum[9], const float[4]){
    nullptr};
  void (*mjv_connector)(mjvGeom *, int, mjtNum, const mjtNum[3], const mjtNum[3]){nullptr};
  void (*mjv_updateScene)(
    const mjModel *, mjData *, const mjvOption *, const mjvPerturb *, mjvCamera *, int, mjvScene *){nullptr};
  void (*mjr_render)(mjrRect, mjvScene *, const mjrContext *){nullptr};
  void (*mjr_freeContext)(mjrContext *){nullptr};
  void (*mjv_freeScene)(mjvScene *){nullptr};

  void load()
  {
    // Bind directly to the linked MuJoCo symbols. stickyskin.cc / object.cc
    // already link libmujoco; a second dlopen re-registers resource encoders
    // and aborts with: resource encoder 'application/zip' is already registered.
    mj_loadXML = ::mj_loadXML;
    mj_compile = ::mj_compile;
    mj_deleteSpec = ::mj_deleteSpec;
    mj_makeData = ::mj_makeData;
    mj_deleteModel = ::mj_deleteModel;
    mj_deleteData = ::mj_deleteData;
    mj_forward = ::mj_forward;
    mj_step = ::mj_step;
    mj_name2id = ::mj_name2id;
    mj_id2name = ::mj_id2name;
    mj_contactForce = ::mj_contactForce;

    mjv_defaultCamera = ::mjv_defaultCamera;
    mjv_defaultOption = ::mjv_defaultOption;
    mjv_defaultScene = ::mjv_defaultScene;
    mjv_defaultPerturb = ::mjv_defaultPerturb;
    mjr_defaultContext = ::mjr_defaultContext;
    mjv_makeScene = ::mjv_makeScene;
    mjr_makeContext = ::mjr_makeContext;
    mjv_moveCamera = ::mjv_moveCamera;
    mjv_applyPerturbForce = ::mjv_applyPerturbForce;
    mjv_initGeom = ::mjv_initGeom;
    mjv_connector = ::mjv_connector;
    mjv_updateScene = ::mjv_updateScene;
    mjr_render = ::mjr_render;
    mjr_freeContext = ::mjr_freeContext;
    mjv_freeScene = ::mjv_freeScene;
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

    const std::string taxel_map_path = declare_parameter<std::string>("taxel_map_path", "");
    build_flex_vertex_taxels(taxel_map_path);

    const std::string joint_topic = declare_parameter<std::string>("joint_topic", "xela_joint_publisher");
    joint_sub_ = create_subscription<sensor_msgs::msg::JointState>(
      joint_topic, rclcpp::QoS(10),
      [this](sensor_msgs::msg::JointState::ConstSharedPtr msg) { this->on_joint_state(std::move(msg)); });

    touch_point_cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>("hand_touch_point_cloud", rclcpp::QoS(10));
    hand_sensors_pub_ = create_publisher<xela_sparshskin_sim::msg::HandSensors>("hand_sensors", rclcpp::QoS(10));

    const std::string perturbation_topic =
      declare_parameter<std::string>("taxel_perturbation_topic", "taxel_perturbation");
    taxel_perturbation_sub_ = create_subscription<xela_sparshskin_sim::msg::TaxelPertubation>(
      perturbation_topic, rclcpp::QoS(10),
      [this](xela_sparshskin_sim::msg::TaxelPertubation::ConstSharedPtr msg) {
        this->on_taxel_perturbation(std::move(msg));
      });

    const int64_t render_hz = declare_parameter<int64_t>("render_hz", 60);
    if (render_hz <= 0) {
      throw std::runtime_error("Parameter 'render_hz' must be > 0");
    }
    render_hz_ = static_cast<double>(render_hz);
    taxel_perturbation_local_frame_ = declare_parameter<bool>("taxel_perturbation_local_frame", true);
    show_mujoco_force_overlay_ = declare_parameter<bool>("show_mujoco_force_overlay", false);
    mujoco_force_arrow_scale_ = declare_parameter<double>("mujoco_force_arrow_scale", 0.020);
    mujoco_force_arrow_width_ = declare_parameter<double>("mujoco_force_arrow_width", 0.0030);
    mujoco_force_max_length_ = declare_parameter<double>("mujoco_force_max_length", 0.040);
    mujoco_force_min_magnitude_ = declare_parameter<double>("mujoco_force_min_magnitude", 0.010);

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
  struct BodyWorldPose
  {
    int joint_id{-1};
    int body_id{-1};
    std::string body_name;
    std::array<double, 3> pos{0.0, 0.0, 0.0};
    std::array<double, 4> quat{1.0, 0.0, 0.0, 0.0};  // (w,x,y,z) in MuJoCo convention
  };

  std::optional<BodyWorldPose> get_body_world_pose_from_joint_locked(const std::string & joint_name) const
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
      "joint='%s' -> body='%s' (jid=%d body_id=%d) pos=[%.6f %.6f %.6f] quat(wxyz)=[%.6f %.6f %.6f %.6f]",
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

  std::string resolve_taxel_map_path(const std::string & param_path) const
  {
    if (!param_path.empty()) {
      return param_path;
    }

    const std::string pkg_share = ament_index_cpp::get_package_share_directory("xela_sparshskin_sim");
    const fs::path share_path = fs::path(pkg_share) / "leap_sensor_taxel_map.json";
    if (fs::exists(share_path)) {
      return share_path.string();
    }

    // Fallback for installs that still place the map next to the executable.
    const fs::path lib_path =
      fs::path(pkg_share).parent_path().parent_path() / "lib" / "xela_sparshskin_sim" / "leap_sensor_taxel_map.json";
    if (fs::exists(lib_path)) {
      return lib_path.string();
    }

    throw std::runtime_error("leap_sensor_taxel_map.json not found under package share or lib");
  }

  void build_flex_vertex_taxels(const std::string & taxel_map_param)
  {
    flex_vertex_taxels_.clear();
    if (!model_) {
      return;
    }

    const std::string map_path = resolve_taxel_map_path(taxel_map_param);
    RCLCPP_INFO(get_logger(), "Loading taxel map: %s", map_path.c_str());

    std::ifstream in(map_path);
    if (!in) {
      throw std::runtime_error("Failed to open taxel map: " + map_path);
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    const JsonValue root = JsonParser(ss.str()).parse();
    const std::unordered_map<std::string, int32_t> name_to_taxel = build_flex_vertex_taxel_id_map(root);

    flex_vertex_taxels_.reserve(name_to_taxel.size());
    for (const auto & kv : name_to_taxel) {
      const std::string & sensor_name = kv.first;
      const int body_id = api_.mj_name2id(model_, mjOBJ_BODY, sensor_name.c_str());
      if (body_id < 0) {
        throw std::runtime_error("Flex vertex body not found in model: " + sensor_name);
      }

      FlexVertexTaxel entry;
      entry.sensor_name = sensor_name;
      entry.taxel_id = kv.second;
      entry.body_id = body_id;

      // Recover flex id / local vertex index from MuJoCo flex vertex tables.
      bool found = false;
      for (int flex_id = 0; flex_id < model_->nflex; ++flex_id) {
        const int vert_adr = model_->flex_vertadr[flex_id];
        const int vert_num = model_->flex_vertnum[flex_id];
        for (int v = 0; v < vert_num; ++v) {
          if (model_->flex_vertbodyid[vert_adr + v] == body_id) {
            entry.flex_id = flex_id;
            entry.vert_index = v;
            found = true;
            break;
          }
        }
        if (found) {
          break;
        }
      }
      if (!found) {
        throw std::runtime_error("Body is not a flex vertex: " + sensor_name);
      }
      flex_vertex_taxels_.push_back(std::move(entry));
    }

    std::sort(
      flex_vertex_taxels_.begin(), flex_vertex_taxels_.end(),
      [](const FlexVertexTaxel & a, const FlexVertexTaxel & b) { return a.taxel_id < b.taxel_id; });

    body_id_by_flex_vertex_name_.clear();
    body_id_by_taxel_id_.clear();
    for (const FlexVertexTaxel & entry : flex_vertex_taxels_) {
      body_id_by_flex_vertex_name_[entry.sensor_name] = entry.body_id;
      body_id_by_taxel_id_[entry.taxel_id] = entry.body_id;
    }

    RCLCPP_INFO(get_logger(), "Mapped %zu flex vertices to taxels", flex_vertex_taxels_.size());
  }

  std::vector<std::array<float, 3>> accumulate_flex_vertex_forces_locked() const
  {
    std::vector<std::array<float, 3>> forces(flex_vertex_taxels_.size(), {0.0f, 0.0f, 0.0f});
    if (!model_ || !data_ || flex_vertex_taxels_.empty()) {
      return forces;
    }

    // Index: flex_id -> (local_vert -> taxel list index)
    std::unordered_map<int, std::vector<int>> flex_vert_to_slot;
    for (size_t i = 0; i < flex_vertex_taxels_.size(); ++i) {
      const FlexVertexTaxel & t = flex_vertex_taxels_[i];
      auto & slots = flex_vert_to_slot[t.flex_id];
      if (static_cast<int>(slots.size()) <= t.vert_index) {
        slots.resize(static_cast<size_t>(t.vert_index) + 1, -1);
      }
      slots[static_cast<size_t>(t.vert_index)] = static_cast<int>(i);
    }

    auto add_force = [&](int flex_id, int vert, float w, const std::array<double, 3> & f_world) {
      const auto it = flex_vert_to_slot.find(flex_id);
      if (it == flex_vert_to_slot.end()) {
        return;
      }
      if (vert < 0 || vert >= static_cast<int>(it->second.size())) {
        return;
      }
      const int slot = it->second[static_cast<size_t>(vert)];
      if (slot < 0) {
        return;
      }
      forces[static_cast<size_t>(slot)][0] += static_cast<float>(w * f_world[0]);
      forces[static_cast<size_t>(slot)][1] += static_cast<float>(w * f_world[1]);
      forces[static_cast<size_t>(slot)][2] += static_cast<float>(w * f_world[2]);
    };

    auto splat_weights = [&](int flex_id, int side, const mjContact & contact)
      -> std::vector<std::pair<int, float>> {
      const int vert = contact.vert[side];
      const int vert_num = model_->flex_vertnum[flex_id];
      if (vert >= 0 && vert < vert_num) {
        return {{vert, 1.0f}};
      }

      const int element = contact.elem[side];
      const int elem_num = model_->flex_elemnum[flex_id];
      const int elem_adr = model_->flex_elemdataadr[flex_id];
      const int vert_adr = model_->flex_vertadr[flex_id];

      if (element < 0 || element >= elem_num) {
        // Fall back to nearest flex vertex.
        int best = 0;
        double best_d2 = std::numeric_limits<double>::infinity();
        for (int v = 0; v < vert_num; ++v) {
          const mjtNum * p = &data_->flexvert_xpos[3 * (vert_adr + v)];
          const double dx = static_cast<double>(p[0] - contact.pos[0]);
          const double dy = static_cast<double>(p[1] - contact.pos[1]);
          const double dz = static_cast<double>(p[2] - contact.pos[2]);
          const double d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < best_d2) {
            best_d2 = d2;
            best = v;
          }
        }
        return {{best, 1.0f}};
      }

      const int * tri = &model_->flex_elem[elem_adr + 3 * element];
      const mjtNum * p0 = &data_->flexvert_xpos[3 * (vert_adr + tri[0])];
      const mjtNum * p1 = &data_->flexvert_xpos[3 * (vert_adr + tri[1])];
      const mjtNum * p2 = &data_->flexvert_xpos[3 * (vert_adr + tri[2])];

      const double e1[3] = {
        static_cast<double>(p1[0] - p0[0]),
        static_cast<double>(p1[1] - p0[1]),
        static_cast<double>(p1[2] - p0[2])};
      const double e2[3] = {
        static_cast<double>(p2[0] - p0[0]),
        static_cast<double>(p2[1] - p0[1]),
        static_cast<double>(p2[2] - p0[2])};
      const double r[3] = {
        static_cast<double>(contact.pos[0] - p0[0]),
        static_cast<double>(contact.pos[1] - p0[1]),
        static_cast<double>(contact.pos[2] - p0[2])};

      // Solve least-squares [e1 e2] x = r for barycentric coords.
      const double a00 = e1[0] * e1[0] + e1[1] * e1[1] + e1[2] * e1[2];
      const double a01 = e1[0] * e2[0] + e1[1] * e2[1] + e1[2] * e2[2];
      const double a11 = e2[0] * e2[0] + e2[1] * e2[1] + e2[2] * e2[2];
      const double b0 = e1[0] * r[0] + e1[1] * r[1] + e1[2] * r[2];
      const double b1 = e2[0] * r[0] + e2[1] * r[1] + e2[2] * r[2];
      const double det = a00 * a11 - a01 * a01;
      double u = 0.0;
      double v = 0.0;
      if (std::abs(det) > 1e-12) {
        u = (a11 * b0 - a01 * b1) / det;
        v = (a00 * b1 - a01 * b0) / det;
      }
      double w0 = 1.0 - u - v;
      double w1 = u;
      double w2 = v;
      w0 = std::max(0.0, w0);
      w1 = std::max(0.0, w1);
      w2 = std::max(0.0, w2);
      const double sum = w0 + w1 + w2;
      if (sum <= 0.0) {
        w0 = w1 = w2 = 1.0 / 3.0;
      } else {
        w0 /= sum;
        w1 /= sum;
        w2 /= sum;
      }
      return {
        {tri[0], static_cast<float>(w0)},
        {tri[1], static_cast<float>(w1)},
        {tri[2], static_cast<float>(w2)},
      };
    };

    for (int contact_id = 0; contact_id < data_->ncon; ++contact_id) {
      const mjContact & contact = data_->contact[contact_id];
      for (int side = 0; side < 2; ++side) {
        const int flex_id = contact.flex[side];
        if (flex_id < 0 || flex_vert_to_slot.find(flex_id) == flex_vert_to_slot.end()) {
          continue;
        }

        mjtNum wrench[6] = {0};
        api_.mj_contactForce(model_, data_, contact_id, wrench);

        // Contact frame rows are world axes; force acts on geom/flex[1].
        const mjtNum * frame = contact.frame;
        std::array<double, 3> force_world = {
          static_cast<double>(frame[0] * wrench[0] + frame[3] * wrench[1] + frame[6] * wrench[2]),
          static_cast<double>(frame[1] * wrench[0] + frame[4] * wrench[1] + frame[7] * wrench[2]),
          static_cast<double>(frame[2] * wrench[0] + frame[5] * wrench[1] + frame[8] * wrench[2]),
        };
        if (side == 0) {
          force_world[0] = -force_world[0];
          force_world[1] = -force_world[1];
          force_world[2] = -force_world[2];
        }

        for (const auto & vw : splat_weights(flex_id, side, contact)) {
          add_force(flex_id, vw.first, vw.second, force_world);
        }
      }
    }

    return forces;
  }

  void publish_hand_sensors_locked()
  {
    if (!hand_sensors_pub_) {
      return;
    }

    // Contact forces from MuJoCo collisions, plus any externally applied
    // taxel perturbations (xfrc_applied), so /hand_sensors reflects both.
    std::vector<std::array<float, 3>> forces = accumulate_flex_vertex_forces_locked();
    for (size_t i = 0; i < flex_vertex_taxels_.size(); ++i) {
      const auto it = applied_xfrc_by_body_id_.find(flex_vertex_taxels_[i].body_id);
      if (it == applied_xfrc_by_body_id_.end()) {
        continue;
      }
      forces[i][0] += static_cast<float>(it->second[0]);
      forces[i][1] += static_cast<float>(it->second[1]);
      forces[i][2] += static_cast<float>(it->second[2]);
    }

    xela_sparshskin_sim::msg::HandSensors msg;
    msg.texels.reserve(flex_vertex_taxels_.size());
    for (size_t i = 0; i < flex_vertex_taxels_.size(); ++i) {
      xela_sparshskin_sim::msg::Texel texel;
      texel.sensor_name = flex_vertex_taxels_[i].sensor_name;
      texel.taxel_id = flex_vertex_taxels_[i].taxel_id;
      texel.fx = forces[i][0];
      texel.fy = forces[i][1];
      texel.fz = forces[i][2];
      msg.texels.push_back(std::move(texel));
    }
    hand_sensors_pub_->publish(std::move(msg));
  }

  std::array<float, 4> force_overlay_rgba(double magnitude) const
  {
    const double t = std::clamp(magnitude / 3.0, 0.0, 1.0);
    return {
      static_cast<float>(0.15 + 0.85 * t),
      static_cast<float>(0.85 - 0.45 * t),
      0.15f,
      1.0f};
  }

  std::array<double, 3> body_local_force_to_world_locked(
    int body_id, const std::array<double, 3> & local_force) const
  {
    if (!model_ || !data_ || body_id < 0 || body_id >= model_->nbody) {
      return local_force;
    }

    const mjtNum * r = &data_->xmat[9 * body_id];
    return {
      static_cast<double>(r[0]) * local_force[0] +
      static_cast<double>(r[1]) * local_force[1] +
      static_cast<double>(r[2]) * local_force[2],
      static_cast<double>(r[3]) * local_force[0] +
      static_cast<double>(r[4]) * local_force[1] +
      static_cast<double>(r[5]) * local_force[2],
      static_cast<double>(r[6]) * local_force[0] +
      static_cast<double>(r[7]) * local_force[1] +
      static_cast<double>(r[8]) * local_force[2]};
  }

  void append_force_overlay_geoms_locked()
  {
    if (!show_mujoco_force_overlay_ || !model_ || !data_ || !scn_.geoms || flex_vertex_taxels_.empty()) {
      return;
    }

    std::vector<std::array<float, 3>> forces = accumulate_flex_vertex_forces_locked();
    for (size_t i = 0; i < flex_vertex_taxels_.size(); ++i) {
      const auto it = applied_xfrc_by_body_id_.find(flex_vertex_taxels_[i].body_id);
      if (it == applied_xfrc_by_body_id_.end()) {
        continue;
      }
      forces[i][0] += static_cast<float>(it->second[0]);
      forces[i][1] += static_cast<float>(it->second[1]);
      forces[i][2] += static_cast<float>(it->second[2]);
    }

    int dropped = 0;
    for (size_t i = 0; i < flex_vertex_taxels_.size(); ++i) {
      const FlexVertexTaxel & taxel = flex_vertex_taxels_[i];
      if (taxel.flex_id < 0 || taxel.flex_id >= model_->nflex) {
        continue;
      }

      const int vert_adr = model_->flex_vertadr[taxel.flex_id];
      const int vert_num = model_->flex_vertnum[taxel.flex_id];
      if (taxel.vert_index < 0 || taxel.vert_index >= vert_num) {
        continue;
      }

      const std::array<float, 3> & force = forces[i];
      const double fx = static_cast<double>(force[0]);
      const double fy = static_cast<double>(force[1]);
      const double fz = static_cast<double>(force[2]);
      const double magnitude = std::sqrt(fx * fx + fy * fy + fz * fz);
      if (magnitude < mujoco_force_min_magnitude_) {
        continue;
      }

      double scale = mujoco_force_arrow_scale_;
      if (mujoco_force_max_length_ > 0.0) {
        scale = std::min(scale, mujoco_force_max_length_ / (magnitude + 1e-12));
      }

      const mjtNum * p = &data_->flexvert_xpos[3 * (vert_adr + taxel.vert_index)];
      const mjtNum from[3] = {p[0], p[1], p[2]};
      const mjtNum to[3] = {
        p[0] + static_cast<mjtNum>(fx * scale),
        p[1] + static_cast<mjtNum>(fy * scale),
        p[2] + static_cast<mjtNum>(fz * scale)};

      if (scn_.ngeom >= scn_.maxgeom) {
        ++dropped;
        continue;
      }

      mjvGeom * geom = scn_.geoms + scn_.ngeom;
      const mjtNum zero[3] = {0, 0, 0};
      const mjtNum mat[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
      const std::array<float, 4> rgba = force_overlay_rgba(magnitude);
      api_.mjv_initGeom(geom, mjGEOM_ARROW, zero, zero, mat, rgba.data());
      api_.mjv_connector(geom, mjGEOM_ARROW, static_cast<mjtNum>(mujoco_force_arrow_width_), from, to);
      geom->objtype = mjOBJ_UNKNOWN;
      geom->objid = -1;
      geom->category = mjCAT_DECOR;
      std::memcpy(geom->rgba, rgba.data(), 4 * sizeof(float));
      ++scn_.ngeom;
    }

    if (dropped > 0) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Dropped %d MuJoCo force overlay geoms because scene is full (maxgeom=%d)",
        dropped, scn_.maxgeom);
    }
  }

  void on_taxel_perturbation(xela_sparshskin_sim::msg::TaxelPertubation::ConstSharedPtr msg)
  {
    if (!msg || !model_ || !data_) {
      return;
    }

    int body_id = -1;
    if (!msg->flex_vertex_id.empty()) {
      const auto it = body_id_by_flex_vertex_name_.find(msg->flex_vertex_id);
      if (it == body_id_by_flex_vertex_name_.end()) {
        RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 2000,
          "Unknown flex_vertex_id='%s'", msg->flex_vertex_id.c_str());
        return;
      }
      body_id = it->second;
    } else {
      const auto it = body_id_by_taxel_id_.find(msg->taxel_id);
      if (it == body_id_by_taxel_id_.end()) {
        RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 2000,
          "Unknown taxel_id=%d", msg->taxel_id);
        return;
      }
      body_id = it->second;
    }

    std::array<double, 3> force_local{0.0, 0.0, 0.0};
    if (msg->force.size() >= 3) {
      force_local = {
        static_cast<double>(msg->force[0]),
        static_cast<double>(msg->force[1]),
        static_cast<double>(msg->force[2])};
    } else if (msg->force.size() == 1) {
      // Allow a scalar push along the taxel-local +Z axis.
      force_local[2] = static_cast<double>(msg->force[0]);
    } else {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "TaxelPertubation.force must have 1 or 3 elements (got %zu)", msg->force.size());
      return;
    }

    const bool clear =
      !std::isfinite(force_local[0]) || !std::isfinite(force_local[1]) || !std::isfinite(force_local[2]) ||
      (std::abs(force_local[0]) < 1e-12 && std::abs(force_local[1]) < 1e-12 &&
      std::abs(force_local[2]) < 1e-12);

    std::lock_guard<std::mutex> lk(mj_mutex_);
    if (clear) {
      applied_xfrc_by_body_id_.erase(body_id);
    } else {
      const std::array<double, 3> force_world =
        taxel_perturbation_local_frame_ ? body_local_force_to_world_locked(body_id, force_local) : force_local;
      applied_xfrc_by_body_id_[body_id] = force_world;
    }
  }

  void apply_external_forces_locked()
  {
    if (!model_ || !data_) {
      return;
    }

    // Clear previous Cartesian wrenches, then write the active set.
    std::fill(data_->xfrc_applied, data_->xfrc_applied + 6 * model_->nbody, 0.0);
    for (const auto & kv : applied_xfrc_by_body_id_) {
      const int body_id = kv.first;
      if (body_id < 0 || body_id >= model_->nbody) {
        continue;
      }
      data_->xfrc_applied[6 * body_id + 0] = kv.second[0];
      data_->xfrc_applied[6 * body_id + 1] = kv.second[1];
      data_->xfrc_applied[6 * body_id + 2] = kv.second[2];
      // torques remain zero
    }

    // MuJoCo simulate.cc-style mouse pull/rotate on the selected body.
    if (pert_.select > 0 && pert_.active) {
      api_.mjv_applyPerturbForce(model_, data_, &pert_);
    }
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

  void on_joint_state(sensor_msgs::msg::JointState::ConstSharedPtr msg)
  {
    if (!msg || msg->name.empty() || msg->position.empty()) {
      return;
    }
    const size_t n = std::min(msg->name.size(), msg->position.size());

    // Latch only — do not touch MuJoCo here. Slider spam used to stall the
    // viewer by running mj_forward on this callback thread.
    std::lock_guard<std::mutex> lk(cmd_mutex_);
    for (size_t i = 0; i < n; ++i) {
      latest_joint_cmd_[msg->name[i]] = msg->position[i];
    }
  }

  // Caller must hold mj_mutex_.
  void update_touch_point_cloud_from_joints_locked(
    const std::unordered_map<std::string, double> & joint_cmds)
  {
    for (const auto & kv : joint_cmds) {
      if (auto pose = get_body_world_pose_from_joint_locked(kv.first)) {
        const std::string key = !pose->body_name.empty() ? pose->body_name : kv.first;
        latest_body_pose_by_body_name_[key] = *pose;
      }
    }
    publish_touch_point_cloud_locked();
  }

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
    fs::path scene = fs::path(xela_description_share) / "mjcf" / "scene_flex_sensor_Box.xml";

    if (!fs::exists(scene)) {
      throw std::runtime_error("scene_flex_sensor_Box.xml not found at: " + scene.string());
    }
    return scene.string();
  }

  void load_mujoco_model(const std::string & scene_path)
  {
    xela_sparshskin_sim::StickySkinParams sticky_params;
    sticky_params.adhesion = declare_parameter<double>("palm_adhesion", 5.0);
    sticky_params.gap = declare_parameter<double>("palm_adhesion_gap", 0.002);

    char err[1024] = {0};
    mjSpec * spec = xela_sparshskin_sim::make_sticky_skin_spec(
      scene_path, sticky_params, err, sizeof(err));
    if (!spec) {
      throw std::runtime_error(std::string("make_sticky_skin_spec failed: ") + err);
    }

    const std::string object_arg = declare_parameter<std::string>("object", "");
    (void)declare_parameter<std::string>("object_type", "cube");
    const bool add_object = !object_arg.empty();
    const std::string object_type = object_arg;
    const std::vector<double> object_size_param =
      declare_parameter<std::vector<double>>("object_size", {0.025, 0.025, 0.025});
    const double object_mass = declare_parameter<double>("object_mass", 0.1);
    const std::vector<double> object_pos_param =
      declare_parameter<std::vector<double>>("object_pos", std::vector<double>{});

    if (add_object) {
      std::array<double, 3> object_size{0.025, 0.025, 0.025};
      if (object_size_param.size() == 1) {
        object_size = {object_size_param[0], object_size_param[0], object_size_param[0]};
      } else if (object_size_param.size() >= 3) {
        object_size = {object_size_param[0], object_size_param[1], object_size_param[2]};
      } else if (!object_size_param.empty()) {
        api_.mj_deleteSpec(spec);
        throw std::runtime_error("Parameter 'object_size' must have 1 or 3 elements");
      }

      xela_sparshskin_sim::create_object object_builder(object_type, object_size, object_mass);
      mjSpec * object_spec = object_builder.make_spec();
      if (!object_spec) {
        api_.mj_deleteSpec(spec);
        throw std::runtime_error("create_object::make_spec failed");
      }

      mjsBody * world = mjs_findBody(spec, "world");
      if (!world) {
        api_.mj_deleteSpec(object_spec);
        api_.mj_deleteSpec(spec);
        throw std::runtime_error("Scene mjSpec has no world body");
      }

      std::array<double, 3> spawn_pos{0.02, 0.12, object_builder.spawn_height()};
      if (object_pos_param.size() >= 3) {
        spawn_pos = {object_pos_param[0], object_pos_param[1], object_pos_param[2]};
      }

      mjsFrame * spawn_frame = mjs_addFrame(world, /*parentframe=*/nullptr);
      if (!spawn_frame) {
        api_.mj_deleteSpec(object_spec);
        api_.mj_deleteSpec(spec);
        throw std::runtime_error("Failed to add object spawn frame");
      }
      mjs_setName(spawn_frame->element, "object_spawn");
      spawn_frame->pos[0] = spawn_pos[0];
      spawn_frame->pos[1] = spawn_pos[1];
      spawn_frame->pos[2] = spawn_pos[2];
      spawn_frame->quat[0] = 1.0;
      spawn_frame->quat[1] = 0.0;
      spawn_frame->quat[2] = 0.0;
      spawn_frame->quat[3] = 0.0;

      mjsBody * object_body = mjs_findBody(object_spec, "object");
      // Deep-copy on attach so the child spec can be freed immediately after.
      mjs_setDeepCopy(spec, /*deepcopy=*/1);
      if (!object_body ||
        mjs_attach(spawn_frame->element, object_body->element, /*prefix=*/"", /*suffix=*/"") ==
        nullptr)
      {
        api_.mj_deleteSpec(object_spec);
        api_.mj_deleteSpec(spec);
        throw std::runtime_error("Failed to attach object mjSpec to scene");
      }
      api_.mj_deleteSpec(object_spec);
      object_spec = nullptr;
      has_free_object_ = true;

      RCLCPP_INFO(
        get_logger(),
        "Will add free object type='%s' size=[%.4f %.4f %.4f] mass=%.3f at [%.3f %.3f %.3f]",
        object_builder.type_name().c_str(),
        object_builder.size()[0], object_builder.size()[1], object_builder.size()[2],
        object_builder.mass(),
        spawn_pos[0], spawn_pos[1], spawn_pos[2]);
    } else {
      has_free_object_ = false;
      RCLCPP_INFO(get_logger(), "No object requested (launch object:=... to spawn one)");
    }

    // Mesh/include paths in the MJCF are relative to the scene directory.
    const fs::path scene_dir = fs::path(scene_path).parent_path();
    const fs::path old_cwd = fs::current_path();
    try {
      fs::current_path(scene_dir);
      model_ = api_.mj_compile(spec, /*vfs=*/nullptr);
      fs::current_path(old_cwd);
    } catch (...) {
      fs::current_path(old_cwd);
      api_.mj_deleteSpec(spec);
      throw;
    }

    if (!model_) {
      const char * cerr = mjs_getError(spec);
      const std::string msg = cerr && cerr[0] ? cerr : "(unknown compile error)";
      api_.mj_deleteSpec(spec);
      throw std::runtime_error(std::string("mj_compile failed: ") + msg);
    }
    api_.mj_deleteSpec(spec);
    spec = nullptr;

    RCLCPP_INFO(
      get_logger(),
      "Compiled sticky-skin model (palm flex_uspa46_* adhesion=%.3f N, gap=%.4f)",
      sticky_params.adhesion, sticky_params.gap);

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
    api_.mjv_defaultPerturb(&pert_);
    api_.mjr_defaultContext(&con_);

    // Show world XYZ axes at the origin (RGB = XYZ).
    opt_.frame = mjFRAME_WORLD;
    model_->vis.scale.framelength = 2.0f;
    model_->vis.scale.framewidth = 0.1f;

    // Free camera must be set explicitly; garbage type trips
    // "mjv_cameraFrame: unknown camera type" and aborts the process.
    cam_.type = mjCAMERA_FREE;
    cam_.fixedcamid = -1;
    cam_.trackbodyid = -1;
    cam_.lookat[0] = 0.02;
    cam_.lookat[1] = 0.08;
    cam_.lookat[2] = 0.10;
    cam_.distance = 0.6;
    cam_.azimuth = 120.0;
    cam_.elevation = -20.0;

    // Flex models can emit many visualization geoms.
    api_.mjv_makeScene(model_, &scn_, 100000);
    api_.mjr_makeContext(model_, &con_, mjFONTSCALE_150);

    camera_control_ = std::make_unique<xela_sparshskin_sim::CameraControl>(
      window_, model_, data_, &cam_, &opt_, &scn_, &pert_,
      api_.mjv_moveCamera, api_.mjv_defaultCamera, &mj_mutex_,
      [this](bool enabled) {
        RCLCPP_INFO(get_logger(), "Adhesion %s (press A to toggle)", enabled ? "ON" : "OFF");
      });
    camera_control_->install();

    RCLCPP_INFO(
      get_logger(),
      "Mouse: drag=camera | double-click=select | Ctrl+right-drag=pull | Ctrl+left-drag=rotate | Esc=clear | A=toggle adhesion");
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
      std::unordered_map<std::string, double> joint_cmds;
      {
        std::lock_guard<std::mutex> cmd_lk(cmd_mutex_);
        joint_cmds = latest_joint_cmd_;
      }

      bool joints_changed = false;
      for (const auto & kv : joint_cmds) {
        joints_changed |= set_joint_qpos_locked(kv.first, kv.second);
      }
      apply_external_forces_locked();
      // Step when a free object is present, mouse perturb is active, or external
      // taxel forces are active so dynamics can run.
      const bool perturb_active = camera_control_ && camera_control_->perturb_active();
      if (has_free_object_ || perturb_active || !applied_xfrc_by_body_id_.empty()) {
        api_.mj_step(model_, data_);
        // Hold commanded hand pose after the step so actuators/dynamics don't drift joints.
        for (const auto & kv : joint_cmds) {
          set_joint_qpos_locked(kv.first, kv.second);
        }
        api_.mj_forward(model_, data_);
      } else {
        api_.mj_forward(model_, data_);
      }
      if (joints_changed || has_free_object_) {
        update_touch_point_cloud_from_joints_locked(joint_cmds);
      }
      publish_hand_sensors_locked();
    }

    mjrRect viewport{0, 0, 0, 0};
    glfwGetFramebufferSize(window_, &viewport.width, &viewport.height);

    {
      std::lock_guard<std::mutex> lk(mj_mutex_);
      api_.mjv_updateScene(model_, data_, &opt_, &pert_, &cam_, mjCAT_ALL, &scn_);
      append_force_overlay_geoms_locked();
      api_.mjr_render(viewport, &scn_, &con_);
    }

    glfwSwapBuffers(window_);
    glfwPollEvents();
  }

  MujocoApi api_;
  mjModel * model_{nullptr};
  mjData * data_{nullptr};
  bool has_free_object_{false};
  std::mutex mj_mutex_;
  std::mutex cmd_mutex_;  // protects latest_joint_cmd_ (callback latch, no MuJoCo)
  std::unordered_map<std::string, int> qpos_index_by_joint_name_;
  std::unordered_map<std::string, double> latest_joint_cmd_;
  std::unordered_map<std::string, BodyWorldPose> latest_body_pose_by_body_name_;
  std::vector<FlexVertexTaxel> flex_vertex_taxels_;
  std::unordered_map<std::string, int> body_id_by_flex_vertex_name_;
  std::unordered_map<int32_t, int> body_id_by_taxel_id_;
  std::unordered_map<int, std::array<double, 3>> applied_xfrc_by_body_id_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_sub_;
  rclcpp::Subscription<xela_sparshskin_sim::msg::TaxelPertubation>::SharedPtr taxel_perturbation_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr touch_point_cloud_pub_;
  rclcpp::Publisher<xela_sparshskin_sim::msg::HandSensors>::SharedPtr hand_sensors_pub_;

  double render_hz_{60.0};
  bool taxel_perturbation_local_frame_{true};
  bool show_mujoco_force_overlay_{true};
  double mujoco_force_arrow_scale_{0.020};
  double mujoco_force_arrow_width_{0.0030};
  double mujoco_force_max_length_{0.040};
  double mujoco_force_min_magnitude_{0.010};
  rclcpp::TimerBase::SharedPtr render_timer_;

  GLFWwindow * window_{nullptr};
  mjvCamera cam_{};
  mjvOption opt_{};
  mjvScene scn_{};
  mjvPerturb pert_{};
  mjrContext con_{};
  std::unique_ptr<xela_sparshskin_sim::CameraControl> camera_control_;
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
