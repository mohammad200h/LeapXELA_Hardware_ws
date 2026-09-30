#include <xela_sparshskin_sim/stickyskin.hpp>

#include <cstdio>
#include <cstring>
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

namespace xela_sparshskin_sim
{
namespace
{

constexpr char kPalmFlexPrefix[] = "flex_uspa46_";

bool starts_with(const char * text, const char * prefix)
{
  if (text == nullptr || prefix == nullptr) {
    return false;
  }
  const std::size_t n = std::strlen(prefix);
  return std::strncmp(text, prefix, n) == 0;
}

void set_error(char * error, int error_sz, const std::string & msg)
{
  if (error == nullptr || error_sz <= 0) {
    return;
  }
  std::snprintf(error, static_cast<std::size_t>(error_sz), "%s", msg.c_str());
}

// Attach a sticky sphere geom to a palm flex vertex body.
bool add_sticky_geom_to_body(mjsBody * body, const StickySkinParams & params, const char * body_name)
{
  if (body == nullptr) {
    return false;
  }

  mjsGeom * geom = mjs_addGeom(body, /*def=*/nullptr);
  if (geom == nullptr) {
    return false;
  }

  const std::string geom_name = std::string(body_name) + "_sticky";
  mjs_setName(geom->element, geom_name.c_str());
  geom->type = mjGEOM_SPHERE;
  geom->size[0] = params.radius;
  geom->size[1] = 0.0;
  geom->size[2] = 0.0;
  // Bit0: grasp objects (default contype/conaffinity 1). Bit1: same partners
  // as palm flexes (floor / probes use 2).
  geom->contype = 3;
  geom->conaffinity = 3;
  geom->condim = 3;
  geom->priority = 1;
  geom->friction[0] = 0.8;
  geom->friction[1] = 0.005;
  geom->friction[2] = 0.0001;
  geom->adhesion = params.adhesion;
  geom->gap = params.gap;
  geom->mass = 0.0;
  geom->density = 0.0;
  geom->group = 3;
  geom->rgba[0] = 1.0f;
  geom->rgba[1] = 0.35f;
  geom->rgba[2] = 0.15f;
  geom->rgba[3] = 0.35f;
  return true;
}

void make_palm_flexes_sticky(mjSpec * spec, const StickySkinParams & params)
{
  // Widen flex gap so adhesive pull can engage slightly before hard contact.
  for (mjsElement * el = mjs_firstElement(spec, mjOBJ_FLEX);
    el != nullptr;
    el = mjs_nextElement(spec, el))
  {
    mjsFlex * flex = mjs_asFlex(el);
    if (flex == nullptr) {
      continue;
    }
    const char * name = mjs_getString(mjs_getName(el));
    if (!starts_with(name, kPalmFlexPrefix)) {
      continue;
    }
    flex->gap = params.gap;
  }

  // Palm flex vertices are bodies named flex_uspa46_*_*.
  for (mjsElement * el = mjs_firstElement(spec, mjOBJ_BODY);
    el != nullptr;
    el = mjs_nextElement(spec, el))
  {
    mjsBody * body = mjs_asBody(el);
    if (body == nullptr) {
      continue;
    }
    const char * name = mjs_getString(mjs_getName(el));
    if (!starts_with(name, kPalmFlexPrefix)) {
      continue;
    }
    add_sticky_geom_to_body(body, params, name);
  }
}

}  // namespace

mjSpec * make_sticky_skin_spec(
  const std::string & xml_path,
  const StickySkinParams & params,
  char * error,
  int error_sz)
{
  if (xml_path.empty()) {
    set_error(error, error_sz, "make_sticky_skin_spec: empty xml_path");
    return nullptr;
  }
  if (!fs::exists(xml_path)) {
    set_error(error, error_sz, "make_sticky_skin_spec: file not found: " + xml_path);
    return nullptr;
  }

  // MJCF <include> resolution is relative to CWD in some MuJoCo setups.
  const fs::path scene_fs(xml_path);
  const fs::path scene_dir = scene_fs.parent_path();
  const fs::path old_cwd = fs::current_path();

  char parse_err[1024] = {0};
  mjSpec * spec = nullptr;
  try {
    fs::current_path(scene_dir);
    spec = mj_parseXML(xml_path.c_str(), /*vfs=*/nullptr, parse_err, sizeof(parse_err));
    fs::current_path(old_cwd);
  } catch (...) {
    fs::current_path(old_cwd);
    throw;
  }

  if (spec == nullptr) {
    set_error(
      error, error_sz,
      std::string("mj_parseXML failed: ") + (parse_err[0] ? parse_err : "(unknown error)"));
    return nullptr;
  }

  make_palm_flexes_sticky(spec, params);
  return spec;
}

}  // namespace xela_sparshskin_sim
