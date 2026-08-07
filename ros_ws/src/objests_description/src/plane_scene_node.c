#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <GLFW/glfw3.h>
#include <mujoco/mujoco.h>
#include <rcl/rcl.h>
#include <rcutils/logging_macros.h>

#include "objests_description/object.h"

#define PACKAGE_NAME "objests_description"
#define DEFAULT_MODEL_RELPATH "share/" PACKAGE_NAME "/mjcf/plane_scene.xml"
#define LOAD_ERROR_SIZE 1000

static mjModel * g_model = NULL;
static mjData * g_data = NULL;
static mjvCamera g_cam;
static mjvOption g_opt;
static mjvScene g_scn;
static mjrContext g_con;
static mjvPerturb g_pert;

static int g_button_left = 0;
static int g_button_middle = 0;
static int g_button_right = 0;
static double g_lastx = 0.0;
static double g_lasty = 0.0;
static int g_lastbutton = 0;
static double g_lastclicktm = 0.0;

static void keyboard(GLFWwindow * window, int key, int scancode, int act, int mods)
{
  (void)window;
  (void)scancode;
  (void)mods;
  if (act == GLFW_PRESS && key == GLFW_KEY_BACKSPACE) {
    mj_resetData(g_model, g_data);
    mj_forward(g_model, g_data);
    g_pert.active = 0;
  }
}

static void mouse_button(GLFWwindow * window, int button, int act, int mods)
{
  g_button_left =
    glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS;
  g_button_middle =
    glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_MIDDLE) == GLFW_PRESS;
  g_button_right =
    glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS;
  glfwGetCursorPos(window, &g_lastx, &g_lasty);

  if (g_model == NULL || g_data == NULL) {
    return;
  }

  /* Ctrl + click starts force/torque perturbation on the selected body. */
  int newperturb = 0;
  if (act == GLFW_PRESS && (mods & GLFW_MOD_CONTROL) && g_pert.select > 0) {
    if (g_button_right) {
      newperturb = mjPERT_TRANSLATE;
    } else if (g_button_left) {
      newperturb = mjPERT_ROTATE;
    }
    if (newperturb && !g_pert.active) {
      mjv_initPerturb(g_model, g_data, &g_scn, &g_pert);
    }
  }
  g_pert.active = newperturb;

  /* Double-click selection / camera lookat / tracking (simulate.cc). */
  if (act == GLFW_PRESS &&
    glfwGetTime() - g_lastclicktm < 0.25 &&
    button == g_lastbutton)
  {
    int selmode;
    if (button == GLFW_MOUSE_BUTTON_LEFT) {
      selmode = 1;  /* select body */
    } else if (mods & GLFW_MOD_CONTROL) {
      selmode = 3;  /* tracking camera */
    } else {
      selmode = 2;  /* center camera lookat */
    }

    int width = 0;
    int height = 0;
    glfwGetWindowSize(window, &width, &height);
    if (width > 0 && height > 0) {
      mjtNum selpnt[3];
      int selgeom = -1;
      int selflex = -1;
      int selskin = -1;
      const int selbody = mjv_select(
        g_model, g_data, &g_opt,
        (mjtNum)width / (mjtNum)height,
        (mjtNum)g_lastx / (mjtNum)width,
        (mjtNum)(height - g_lasty) / (mjtNum)height,
        &g_scn, selpnt, &selgeom, &selflex, &selskin);

      if (selmode == 2 || selmode == 3) {
        if (selbody >= 0) {
          mju_copy3(g_cam.lookat, selpnt);
        }
        if (selmode == 3 && selbody > 0) {
          g_cam.type = mjCAMERA_TRACKING;
          g_cam.trackbodyid = selbody;
          g_cam.fixedcamid = -1;
        }
      } else if (selbody > 0) {
        g_pert.select = selbody;
        g_pert.flexselect = selflex;
        g_pert.skinselect = selskin;
        mjtNum tmp[3];
        mju_sub3(tmp, selpnt, g_data->xpos + 3 * g_pert.select);
        mju_mulMatTVec(
          g_pert.localpos, g_data->xmat + 9 * g_pert.select, tmp, 3, 3);
      } else {
        g_pert.select = 0;
        g_pert.flexselect = -1;
        g_pert.skinselect = -1;
      }
    }
    g_pert.active = 0;
  }

  if (act == GLFW_PRESS) {
    g_lastbutton = button;
    g_lastclicktm = glfwGetTime();
  }
}

static void mouse_move(GLFWwindow * window, double xpos, double ypos)
{
  if (!g_button_left && !g_button_middle && !g_button_right) {
    return;
  }

  const double dx = xpos - g_lastx;
  const double dy = ypos - g_lasty;
  g_lastx = xpos;
  g_lasty = ypos;

  int width = 0;
  int height = 0;
  glfwGetWindowSize(window, &width, &height);
  if (height <= 0) {
    return;
  }

  const int mod_shift =
    glfwGetKey(window, GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS ||
    glfwGetKey(window, GLFW_KEY_RIGHT_SHIFT) == GLFW_PRESS;

  mjtMouse action;
  if (g_button_right) {
    action = mod_shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V;
  } else if (g_button_left) {
    action = mod_shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V;
  } else {
    action = mjMOUSE_ZOOM;
  }

  if (g_pert.active) {
    mjv_movePerturb(
      g_model, g_data, action, dx / height, dy / height, &g_scn, &g_pert);
  } else {
    mjv_moveCamera(g_model, action, dx / height, dy / height, &g_cam);
  }
}

static void scroll(GLFWwindow * window, double xoffset, double yoffset)
{
  (void)window;
  (void)xoffset;
  mjv_moveCamera(g_model, mjMOUSE_ZOOM, 0, -0.05 * yoffset, &g_cam);
}

/* Resolve share/<pkg>/mjcf/plane_scene.xml via AMENT_PREFIX_PATH. */
static int resolve_default_model_path(char * out, size_t out_size)
{
  const char * prefix_path = getenv("AMENT_PREFIX_PATH");
  if (prefix_path == NULL || prefix_path[0] == '\0') {
    return 0;
  }

  char * prefixes = strdup(prefix_path);
  if (prefixes == NULL) {
    return 0;
  }

  int found = 0;
  char * saveptr = NULL;
  for (char * prefix = strtok_r(prefixes, ":", &saveptr);
    prefix != NULL;
    prefix = strtok_r(NULL, ":", &saveptr))
  {
    int n = snprintf(out, out_size, "%s/%s", prefix, DEFAULT_MODEL_RELPATH);
    if (n < 0 || (size_t)n >= out_size) {
      continue;
    }
    FILE * f = fopen(out, "r");
    if (f != NULL) {
      fclose(f);
      found = 1;
      break;
    }
  }

  free(prefixes);
  return found;
}

static void cleanup_rcl(
  rcl_node_t * node,
  rcl_context_t * context,
  rcl_init_options_t * init_options,
  int node_inited)
{
  rcl_ret_t ignored;
  if (node_inited) {
    ignored = rcl_node_fini(node);
  }
  ignored = rcl_shutdown(context);
  ignored = rcl_context_fini(context);
  ignored = rcl_init_options_fini(init_options);
  (void)ignored;
}

int main(int argc, const char ** argv)
{
  rcl_ret_t ret;
  rcl_allocator_t allocator = rcl_get_default_allocator();
  rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
  ret = rcl_init_options_init(&init_options, allocator);
  if (ret != RCL_RET_OK) {
    fprintf(stderr, "Failed to init rcl options\n");
    return EXIT_FAILURE;
  }

  rcl_context_t context = rcl_get_zero_initialized_context();
  ret = rcl_init(argc, argv, &init_options, &context);
  if (ret != RCL_RET_OK) {
    fprintf(stderr, "Failed to init rcl\n");
    {
      rcl_ret_t ignored = rcl_init_options_fini(&init_options);
      (void)ignored;
    }
    return EXIT_FAILURE;
  }

  rcl_node_t node = rcl_get_zero_initialized_node();
  rcl_node_options_t node_options = rcl_node_get_default_options();
  ret = rcl_node_init(&node, "plane_scene_node", "", &context, &node_options);
  if (ret != RCL_RET_OK) {
    fprintf(stderr, "Failed to create node\n");
    cleanup_rcl(&node, &context, &init_options, 0);
    return EXIT_FAILURE;
  }

  ObjectParams object_params;
  object_params_default(&object_params);
  if (object_params_parse_args(argc, argv, &object_params) != 0) {
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  char model_path[1024];
  if (argc >= 2 && argv[1] != NULL && argv[1][0] != '-') {
    snprintf(model_path, sizeof(model_path), "%s", argv[1]);
  } else if (!resolve_default_model_path(model_path, sizeof(model_path))) {
    RCUTILS_LOG_ERROR_NAMED(
      PACKAGE_NAME,
      "Could not find default model '%s'. Pass an MJCF path as argv[1].",
      DEFAULT_MODEL_RELPATH);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  char load_error[LOAD_ERROR_SIZE] = "Could not load model";
  mjSpec * scene_spec = mj_parseXML(model_path, NULL, load_error, LOAD_ERROR_SIZE);
  if (scene_spec == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Parse scene error: %s", load_error);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  mjSpec * object_spec = get_object_spec(&object_params);
  if (object_spec == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "get_object_spec failed");
    mj_deleteSpec(scene_spec);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  mjsBody * world = mjs_findBody(scene_spec, "world");
  mjsBody * object_body = mjs_findBody(object_spec, "object");
  if (world == NULL || object_body == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Missing world or object body for attach");
    mj_deleteSpec(object_spec);
    mj_deleteSpec(scene_spec);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  mjsFrame * spawn = mjs_addFrame(world, NULL);
  if (spawn == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Failed to create spawn frame");
    mj_deleteSpec(object_spec);
    mj_deleteSpec(scene_spec);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }
  mjs_setName(spawn->element, "object_spawn");
  spawn->pos[0] = 0.0;
  spawn->pos[1] = 0.0;
  spawn->pos[2] = object_spawn_height(&object_params);

  /* Deep-copy so object_spec remains independently freeable. */
  mjs_setDeepCopy(scene_spec, 1);
  mjsElement * attached = mjs_attach(spawn->element, object_body->element, "", "");
  if (attached == NULL) {
    RCUTILS_LOG_ERROR_NAMED(
      PACKAGE_NAME, "Failed to attach object: %s", mjs_getError(scene_spec));
    mj_deleteSpec(object_spec);
    mj_deleteSpec(scene_spec);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  g_model = mj_compile(scene_spec, NULL);
  if (g_model == NULL) {
    RCUTILS_LOG_ERROR_NAMED(
      PACKAGE_NAME, "Compile error: %s", mjs_getError(scene_spec));
    mj_deleteSpec(object_spec);
    mj_deleteSpec(scene_spec);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  mj_deleteSpec(object_spec);
  mj_deleteSpec(scene_spec);

  g_data = mj_makeData(g_model);
  if (g_data == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Failed to allocate mjData");
    mj_deleteModel(g_model);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  if (!glfwInit()) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Could not initialize GLFW");
    mj_deleteData(g_data);
    mj_deleteModel(g_model);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }

  GLFWwindow * window = glfwCreateWindow(1200, 900, "MuJoCo plane scene", NULL, NULL);
  if (window == NULL) {
    RCUTILS_LOG_ERROR_NAMED(PACKAGE_NAME, "Could not create GLFW window");
    glfwTerminate();
    mj_deleteData(g_data);
    mj_deleteModel(g_model);
    cleanup_rcl(&node, &context, &init_options, 1);
    return EXIT_FAILURE;
  }
  glfwMakeContextCurrent(window);
  glfwSwapInterval(1);

  mjv_defaultCamera(&g_cam);
  mjv_defaultOption(&g_opt);
  mjv_defaultScene(&g_scn);
  mjr_defaultContext(&g_con);
  mjv_defaultPerturb(&g_pert);
  mjv_makeScene(g_model, &g_scn, 2000);
  mjr_makeContext(g_model, &g_con, mjFONTSCALE_150);

  glfwSetKeyCallback(window, keyboard);
  glfwSetCursorPosCallback(window, mouse_move);
  glfwSetMouseButtonCallback(window, mouse_button);
  glfwSetScrollCallback(window, scroll);

  RCUTILS_LOG_INFO_NAMED(
    PACKAGE_NAME,
    "Loaded scene '%s' with object type=%s size=[%.3f %.3f %.3f] "
    "friction=[%.3f %.3f %.3f] adhesion=%.3f",
    model_path,
    object_type_name(object_params.type),
    object_params.size[0], object_params.size[1], object_params.size[2],
    object_params.friction[0], object_params.friction[1], object_params.friction[2],
    object_params.adhesion);
  RCUTILS_LOG_INFO_NAMED(
    PACKAGE_NAME,
    "Controls: double-click select | Ctrl+right-drag pull | "
    "Ctrl+left-drag torque | Backspace reset");

  while (rcl_context_is_valid(&context) && !glfwWindowShouldClose(window)) {
    const mjtNum simstart = g_data->time;
    while (g_data->time - simstart < 1.0 / 60.0) {
      /* Clear leftover forces, then apply mouse perturbation (simulate.cc). */
      mju_zero(g_data->xfrc_applied, 6 * g_model->nbody);
      mjv_applyPerturbPose(g_model, g_data, &g_pert, 0);
      mjv_applyPerturbForce(g_model, g_data, &g_pert);
      mj_step(g_model, g_data);
    }

    mjrRect viewport = {0, 0, 0, 0};
    glfwGetFramebufferSize(window, &viewport.width, &viewport.height);
    mjv_updateScene(g_model, g_data, &g_opt, &g_pert, &g_cam, mjCAT_ALL, &g_scn);
    mjr_render(viewport, &g_scn, &g_con);

    glfwSwapBuffers(window);
    glfwPollEvents();
  }

  mjv_freeScene(&g_scn);
  mjr_freeContext(&g_con);
  mj_deleteData(g_data);
  mj_deleteModel(g_model);

#if defined(__APPLE__) || defined(_WIN32)
  glfwTerminate();
#endif

  cleanup_rcl(&node, &context, &init_options, 1);
  return EXIT_SUCCESS;
}
