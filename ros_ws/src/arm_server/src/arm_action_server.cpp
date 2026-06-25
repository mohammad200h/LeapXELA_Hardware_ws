#include <cmath>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <cctype>

#include "arm_server/action/execute.hpp"
#include "arm_server/action/plan.hpp"
#include "arm_server/action/update_planning_scene.hpp"
#include "arm_server/msg/scene_object.hpp"
#include "geometry_msgs/msg/pose.hpp"
#include "moveit/move_group_interface/move_group_interface.h"
#include "moveit/planning_scene_interface/planning_scene_interface.h"
#include "moveit_msgs/msg/collision_object.hpp"
#include "moveit_msgs/msg/object_color.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "shape_msgs/msg/solid_primitive.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using Plan = arm_server::action::Plan;
using Execute = arm_server::action::Execute;
using UpdatePlanningScene = arm_server::action::UpdatePlanningScene;
using GoalHandlePlan = rclcpp_action::ServerGoalHandle<Plan>;
using GoalHandleExecute = rclcpp_action::ServerGoalHandle<Execute>;
using GoalHandleUpdatePlanningScene = rclcpp_action::ServerGoalHandle<UpdatePlanningScene>;

struct StoredPlan
{
  moveit::planning_interface::MoveGroupInterface::Plan plan;
};

class ArmActionServer : public rclcpp::Node
{
public:
  template<typename T>
  T get_or_declare_parameter(const std::string & name, const T & default_value)
  {
    if (!this->has_parameter(name)) {
      return this->declare_parameter<T>(name, default_value);
    }
    return this->get_parameter(name).get_value<T>();
  }

  explicit ArmActionServer(const rclcpp::NodeOptions & options = rclcpp::NodeOptions())
  : Node("arm_action_server", options)
  {
    planning_group_ = get_or_declare_parameter<std::string>("planning_group", "panda_arm");
    end_effector_link_ = get_or_declare_parameter<std::string>("end_effector_link", "panda_link8");
    planning_frame_ = get_or_declare_parameter<std::string>("planning_frame", "panda_link0");
    planning_time_ = get_or_declare_parameter<double>("planning_time", 5.0);
    max_velocity_scaling_ = get_or_declare_parameter<double>("max_velocity_scaling", 0.2);
    max_acceleration_scaling_ = get_or_declare_parameter<double>("max_acceleration_scaling", 0.2);

    plan_action_server_ = rclcpp_action::create_server<Plan>(
      this,
      "plan",
      std::bind(&ArmActionServer::handle_plan_goal, this, std::placeholders::_1, std::placeholders::_2),
      std::bind(&ArmActionServer::handle_plan_cancel, this, std::placeholders::_1),
      std::bind(&ArmActionServer::handle_plan_accepted, this, std::placeholders::_1));

    execute_action_server_ = rclcpp_action::create_server<Execute>(
      this,
      "execute",
      std::bind(&ArmActionServer::handle_execute_goal, this, std::placeholders::_1, std::placeholders::_2),
      std::bind(&ArmActionServer::handle_execute_cancel, this, std::placeholders::_1),
      std::bind(&ArmActionServer::handle_execute_accepted, this, std::placeholders::_1));

    update_planning_scene_action_server_ = rclcpp_action::create_server<UpdatePlanningScene>(
      this,
      "update_planning_scene",
      std::bind(
        &ArmActionServer::handle_update_planning_scene_goal, this, std::placeholders::_1,
        std::placeholders::_2),
      std::bind(
        &ArmActionServer::handle_update_planning_scene_cancel, this, std::placeholders::_1),
      std::bind(
        &ArmActionServer::handle_update_planning_scene_accepted, this, std::placeholders::_1));

    RCLCPP_INFO(
      this->get_logger(),
      "Arm action server ready. Actions: /plan, /execute, /update_planning_scene. "
      "planning_group='%s', end_effector_link='%s'",
      planning_group_.c_str(), end_effector_link_.c_str());
  }

private:
  rclcpp_action::Server<Plan>::SharedPtr plan_action_server_;
  rclcpp_action::Server<Execute>::SharedPtr execute_action_server_;
  rclcpp_action::Server<UpdatePlanningScene>::SharedPtr update_planning_scene_action_server_;
  std::unique_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
  std::unique_ptr<moveit::planning_interface::PlanningSceneInterface> planning_scene_interface_;
  std::mutex move_group_mutex_;
  std::mutex planning_scene_mutex_;
  std::vector<std::string> tracked_scene_object_ids_;

  std::mutex plans_mutex_;
  std::unordered_map<uint64_t, StoredPlan> stored_plans_;
  uint64_t next_plan_id_{1};
  uint64_t latest_plan_id_{0};

  std::string planning_group_;
  std::string end_effector_link_;
  std::string planning_frame_;
  double planning_time_;
  double max_velocity_scaling_;
  double max_acceleration_scaling_;

  void ensure_robot_description_available()
  {
    std::string robot_description;
    std::string robot_description_semantic;
    if (!this->get_parameter("robot_description", robot_description) ||
      robot_description.empty() ||
      !this->get_parameter("robot_description_semantic", robot_description_semantic) ||
      robot_description_semantic.empty())
    {
      throw std::runtime_error(
        "Missing robot_description or robot_description_semantic. "
        "Start the node with: ros2 launch arm_server arm_action_server.launch.py");
    }
  }

  moveit::planning_interface::MoveGroupInterface & get_move_group()
  {
    std::lock_guard<std::mutex> lock(move_group_mutex_);
    if (!move_group_) {
      ensure_robot_description_available();
      auto node_ptr = std::shared_ptr<rclcpp::Node>(this, [](auto *) {});
      move_group_ = std::make_unique<moveit::planning_interface::MoveGroupInterface>(
        node_ptr, planning_group_);
      move_group_->setEndEffectorLink(end_effector_link_);
      move_group_->setPoseReferenceFrame(planning_frame_);
      move_group_->setPlanningTime(planning_time_);
      move_group_->setMaxVelocityScalingFactor(max_velocity_scaling_);
      move_group_->setMaxAccelerationScalingFactor(max_acceleration_scaling_);
    }
    return *move_group_;
  }

  moveit::planning_interface::PlanningSceneInterface & get_planning_scene_interface()
  {
    std::lock_guard<std::mutex> lock(planning_scene_mutex_);
    if (!planning_scene_interface_) {
      planning_scene_interface_ =
        std::make_unique<moveit::planning_interface::PlanningSceneInterface>();
    }
    return *planning_scene_interface_;
  }

  static std::string to_lower(std::string value)
  {
    for (auto & character : value) {
      character = static_cast<char>(std::tolower(static_cast<unsigned char>(character)));
    }
    return value;
  }

  std::optional<moveit_msgs::msg::CollisionObject> build_collision_object(
    const arm_server::msg::SceneObject & object,
    const std::string & fallback_id)
  {
    moveit_msgs::msg::CollisionObject collision_object;
    collision_object.header.frame_id = planning_frame_;
    collision_object.id = object.id.empty() ? fallback_id : object.id;

    shape_msgs::msg::SolidPrimitive primitive;
    const std::string shape_type = to_lower(object.shape_type);
    if (shape_type == "box") {
      if (object.dimensions.size() != 3) {
        return std::nullopt;
      }
      primitive.type = shape_msgs::msg::SolidPrimitive::BOX;
    } else if (shape_type == "sphere") {
      if (object.dimensions.size() != 1) {
        return std::nullopt;
      }
      primitive.type = shape_msgs::msg::SolidPrimitive::SPHERE;
    } else if (shape_type == "cylinder") {
      if (object.dimensions.size() != 2) {
        return std::nullopt;
      }
      primitive.type = shape_msgs::msg::SolidPrimitive::CYLINDER;
    } else {
      return std::nullopt;
    }

    primitive.dimensions.clear();
    for (const auto dimension : object.dimensions) {
      primitive.dimensions.push_back(dimension);
    }

    collision_object.primitives.push_back(primitive);
    collision_object.primitive_poses.push_back(
      pose_from_xyz_rpy(object.x, object.y, object.z, object.roll, object.pitch, object.yaw));
    collision_object.operation = moveit_msgs::msg::CollisionObject::ADD;
    return collision_object;
  }

  static geometry_msgs::msg::Pose pose_from_xyz_rpy(
    double x, double y, double z, double roll, double pitch, double yaw)
  {
    geometry_msgs::msg::Pose pose;
    pose.position.x = x;
    pose.position.y = y;
    pose.position.z = z;

    tf2::Quaternion quaternion;
    quaternion.setRPY(roll, pitch, yaw);
    pose.orientation = tf2::toMsg(quaternion);
    return pose;
  }

  static double trajectory_duration(
    const moveit::planning_interface::MoveGroupInterface::Plan & plan)
  {
    if (plan.trajectory_.joint_trajectory.points.empty()) {
      return 0.0;
    }
    const auto & last_point = plan.trajectory_.joint_trajectory.points.back();
    return rclcpp::Duration(last_point.time_from_start).seconds();
  }

  uint64_t store_plan(const moveit::planning_interface::MoveGroupInterface::Plan & plan)
  {
    std::lock_guard<std::mutex> lock(plans_mutex_);
    const uint64_t plan_id = next_plan_id_++;
    stored_plans_[plan_id] = StoredPlan{plan};
    latest_plan_id_ = plan_id;
    return plan_id;
  }

  bool get_stored_plan(
    uint64_t plan_id,
    moveit::planning_interface::MoveGroupInterface::Plan & plan,
    uint64_t & resolved_plan_id)
  {
    std::lock_guard<std::mutex> lock(plans_mutex_);
    resolved_plan_id = plan_id == 0 ? latest_plan_id_ : plan_id;
    if (resolved_plan_id == 0) {
      return false;
    }

    const auto iterator = stored_plans_.find(resolved_plan_id);
    if (iterator == stored_plans_.end()) {
      return false;
    }

    plan = iterator->second.plan;
    return true;
  }

  void remove_stored_plan(uint64_t plan_id)
  {
    std::lock_guard<std::mutex> lock(plans_mutex_);
    stored_plans_.erase(plan_id);
  }

  rclcpp_action::GoalResponse handle_plan_goal(
    const rclcpp_action::GoalUUID & /*uuid*/,
    std::shared_ptr<const Plan::Goal> goal)
  {
    RCLCPP_INFO(
      this->get_logger(),
      "Received plan goal: xyz=[%.3f, %.3f, %.3f], rpy=[%.3f, %.3f, %.3f]",
      goal->x, goal->y, goal->z, goal->roll, goal->pitch, goal->yaw);
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_plan_cancel(
    const std::shared_ptr<GoalHandlePlan> /*goal_handle*/)
  {
    RCLCPP_INFO(this->get_logger(), "Received request to cancel plan goal");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_plan_accepted(const std::shared_ptr<GoalHandlePlan> goal_handle)
  {
    std::thread{std::bind(&ArmActionServer::execute_plan, this, std::placeholders::_1), goal_handle}
    .detach();
  }

  rclcpp_action::GoalResponse handle_execute_goal(
    const rclcpp_action::GoalUUID & /*uuid*/,
    std::shared_ptr<const Execute::Goal> goal)
  {
    RCLCPP_INFO(this->get_logger(), "Received execute goal for plan_id=%lu", goal->plan_id);
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_execute_cancel(
    const std::shared_ptr<GoalHandleExecute> /*goal_handle*/)
  {
    RCLCPP_INFO(this->get_logger(), "Received request to cancel execute goal");
    std::lock_guard<std::mutex> lock(move_group_mutex_);
    if (move_group_) {
      move_group_->stop();
    }
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_execute_accepted(const std::shared_ptr<GoalHandleExecute> goal_handle)
  {
    std::thread{
      std::bind(&ArmActionServer::execute_trajectory, this, std::placeholders::_1), goal_handle}
    .detach();
  }

  rclcpp_action::GoalResponse handle_update_planning_scene_goal(
    const rclcpp_action::GoalUUID & /*uuid*/,
    std::shared_ptr<const UpdatePlanningScene::Goal> goal)
  {
    RCLCPP_INFO(
      this->get_logger(),
      "Received update_planning_scene goal with %zu object(s), clear_existing=%s",
      goal->objects.size(), goal->clear_existing ? "true" : "false");
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_update_planning_scene_cancel(
    const std::shared_ptr<GoalHandleUpdatePlanningScene> /*goal_handle*/)
  {
    RCLCPP_INFO(this->get_logger(), "Received request to cancel update_planning_scene goal");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_update_planning_scene_accepted(
    const std::shared_ptr<GoalHandleUpdatePlanningScene> goal_handle)
  {
    std::thread{
      std::bind(&ArmActionServer::update_planning_scene, this, std::placeholders::_1), goal_handle}
    .detach();
  }

  void execute_plan(const std::shared_ptr<GoalHandlePlan> goal_handle)
  {
    const auto goal = goal_handle->get_goal();
    auto feedback = std::make_shared<Plan::Feedback>();
    auto result = std::make_shared<Plan::Result>();

    feedback->progress = 0.0;
    goal_handle->publish_feedback(feedback);

    try {
      auto & move_group = get_move_group();
      const auto target_pose = pose_from_xyz_rpy(
        goal->x, goal->y, goal->z, goal->roll, goal->pitch, goal->yaw);

      if (!move_group.setPoseTarget(target_pose, end_effector_link_)) {
        result->success = false;
        result->message = "Failed to set pose target for end effector link: " + end_effector_link_;
        result->plan_id = 0;
        result->trajectory_duration = 0.0;
        goal_handle->abort(result);
        RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
        return;
      }

      feedback->progress = 0.5;
      goal_handle->publish_feedback(feedback);

      moveit::planning_interface::MoveGroupInterface::Plan plan;
      const auto plan_result = move_group.plan(plan);
      if (goal_handle->is_canceling()) {
        result->success = false;
        result->message = "Plan goal canceled";
        result->plan_id = 0;
        result->trajectory_duration = 0.0;
        goal_handle->canceled(result);
        return;
      }

      if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
        result->success = false;
        result->message = "MoveIt planning failed with error code: " +
          std::to_string(static_cast<int>(plan_result.val));
        result->plan_id = 0;
        result->trajectory_duration = 0.0;
        goal_handle->abort(result);
        RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
        return;
      }

      const uint64_t plan_id = store_plan(plan);
      feedback->progress = 1.0;
      goal_handle->publish_feedback(feedback);

      result->success = true;
      result->message = "Planning succeeded";
      result->plan_id = plan_id;
      result->trajectory_duration = trajectory_duration(plan);
      goal_handle->succeed(result);
      RCLCPP_INFO(
        this->get_logger(), "Plan succeeded. plan_id=%lu, duration=%.2fs",
        plan_id, result->trajectory_duration);
    } catch (const std::exception & exception) {
      result->success = false;
      result->message = std::string("MoveIt planning error: ") + exception.what();
      result->plan_id = 0;
      result->trajectory_duration = 0.0;
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    } catch (...) {
      result->success = false;
      result->message = "Unknown MoveIt error while planning";
      result->plan_id = 0;
      result->trajectory_duration = 0.0;
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    }
  }

  void execute_trajectory(const std::shared_ptr<GoalHandleExecute> goal_handle)
  {
    const auto goal = goal_handle->get_goal();
    auto feedback = std::make_shared<Execute::Feedback>();
    auto result = std::make_shared<Execute::Result>();

    feedback->progress = 0.0;
    goal_handle->publish_feedback(feedback);

    try {
      moveit::planning_interface::MoveGroupInterface::Plan plan;
      uint64_t resolved_plan_id = 0;
      if (!get_stored_plan(goal->plan_id, plan, resolved_plan_id)) {
        result->success = false;
        result->message = goal->plan_id == 0 ?
          "No stored plan available. Call /plan first." :
          "Unknown plan_id: " + std::to_string(goal->plan_id);
        goal_handle->abort(result);
        RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
        return;
      }

      auto & move_group = get_move_group();

      feedback->progress = 0.1;
      goal_handle->publish_feedback(feedback);
      RCLCPP_INFO(this->get_logger(), "Executing stored plan_id=%lu", resolved_plan_id);

      const auto execute_result = move_group.execute(plan);
      if (goal_handle->is_canceling()) {
        result->success = false;
        result->message = "Execute goal canceled";
        goal_handle->canceled(result);
        return;
      }

      if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
        result->success = false;
        result->message = "MoveIt execution failed with error code: " +
          std::to_string(static_cast<int>(execute_result.val));
        goal_handle->abort(result);
        RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
        return;
      }

      remove_stored_plan(resolved_plan_id);
      feedback->progress = 1.0;
      goal_handle->publish_feedback(feedback);

      result->success = true;
      result->message = "Trajectory executed successfully";
      goal_handle->succeed(result);
      RCLCPP_INFO(this->get_logger(), "Execute succeeded for plan_id=%lu", resolved_plan_id);
    } catch (const std::exception & exception) {
      result->success = false;
      result->message = std::string("MoveIt execution error: ") + exception.what();
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    } catch (...) {
      result->success = false;
      result->message = "Unknown MoveIt error while executing";
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    }
  }

  void update_planning_scene(const std::shared_ptr<GoalHandleUpdatePlanningScene> goal_handle)
  {
    const auto goal = goal_handle->get_goal();
    auto feedback = std::make_shared<UpdatePlanningScene::Feedback>();
    auto result = std::make_shared<UpdatePlanningScene::Result>();

    feedback->progress = 0.0;
    goal_handle->publish_feedback(feedback);

    try {
      auto & planning_scene_interface = get_planning_scene_interface();

      if (goal->clear_existing) {
        std::lock_guard<std::mutex> lock(planning_scene_mutex_);
        if (!tracked_scene_object_ids_.empty()) {
          planning_scene_interface.removeCollisionObjects(tracked_scene_object_ids_);
          tracked_scene_object_ids_.clear();
        }
      }

      if (goal->objects.empty()) {
        feedback->progress = 1.0;
        goal_handle->publish_feedback(feedback);
        result->success = true;
        result->message = goal->clear_existing ?
          "Cleared previously tracked planning scene objects" :
          "No objects provided";
        result->objects_added = 0;
        goal_handle->succeed(result);
        return;
      }

      std::vector<moveit_msgs::msg::CollisionObject> collision_objects;
      std::vector<moveit_msgs::msg::ObjectColor> object_colors;
      collision_objects.reserve(goal->objects.size());

      for (size_t index = 0; index < goal->objects.size(); ++index) {
        const auto fallback_id = "scene_object_" + std::to_string(index);
        const auto collision_object = build_collision_object(goal->objects[index], fallback_id);
        if (!collision_object) {
          result->success = false;
          result->message = "Invalid object at index " + std::to_string(index) +
            ". shape_type must be box, sphere, or cylinder with the correct number of dimensions.";
          result->objects_added = 0;
          goal_handle->abort(result);
          RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
          return;
        }
        collision_objects.push_back(*collision_object);

        if (goal->objects[index].use_color) {
          moveit_msgs::msg::ObjectColor object_color;
          object_color.id = collision_objects.back().id;
          object_color.color.r = goal->objects[index].color_r;
          object_color.color.g = goal->objects[index].color_g;
          object_color.color.b = goal->objects[index].color_b;
          object_color.color.a = goal->objects[index].color_a;
          object_colors.push_back(object_color);
        }
      }

      feedback->progress = 0.5;
      goal_handle->publish_feedback(feedback);

      if (!planning_scene_interface.applyCollisionObjects(collision_objects, object_colors)) {
        result->success = false;
        result->message = "Failed to apply collision objects to the MoveIt planning scene";
        result->objects_added = 0;
        goal_handle->abort(result);
        RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
        return;
      }

      {
        std::lock_guard<std::mutex> lock(planning_scene_mutex_);
        for (const auto & collision_object : collision_objects) {
          const auto iterator = std::find(
            tracked_scene_object_ids_.begin(), tracked_scene_object_ids_.end(), collision_object.id);
          if (iterator == tracked_scene_object_ids_.end()) {
            tracked_scene_object_ids_.push_back(collision_object.id);
          }
        }
      }

      feedback->progress = 1.0;
      goal_handle->publish_feedback(feedback);

      result->success = true;
      result->message = "Planning scene updated successfully";
      result->objects_added = static_cast<uint32_t>(collision_objects.size());
      goal_handle->succeed(result);
      RCLCPP_INFO(
        this->get_logger(), "Added %u object(s) to the MoveIt planning scene",
        result->objects_added);
    } catch (const std::exception & exception) {
      result->success = false;
      result->message = std::string("MoveIt planning scene error: ") + exception.what();
      result->objects_added = 0;
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    } catch (...) {
      result->success = false;
      result->message = "Unknown MoveIt error while updating the planning scene";
      result->objects_added = 0;
      goal_handle->abort(result);
      RCLCPP_ERROR(this->get_logger(), "%s", result->message.c_str());
    }
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  rclcpp::NodeOptions options;
  options.automatically_declare_parameters_from_overrides(true);

  auto node = std::make_shared<ArmActionServer>(options);
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
