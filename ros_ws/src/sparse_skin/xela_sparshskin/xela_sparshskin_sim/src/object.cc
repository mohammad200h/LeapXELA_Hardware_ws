#include <xela_sparshskin_sim/object.hpp>

#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <string>

namespace xela_sparshskin_sim
{
namespace
{

std::string to_lower(std::string s)
{
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });
  return s;
}

}  // namespace

mjtGeom create_object::parse_type(const std::string & type)
{
  const std::string t = to_lower(type);
  if (t == "cube" || t == "box") {
    return mjGEOM_BOX;
  }
  if (t == "sphere") {
    return mjGEOM_SPHERE;
  }
  if (t == "cylinder") {
    return mjGEOM_CYLINDER;
  }
  if (t == "capsule") {
    return mjGEOM_CAPSULE;
  }
  if (t == "ellipsoid") {
    return mjGEOM_ELLIPSOID;
  }
  throw std::invalid_argument(
    "create_object: unknown type '" + type +
    "' (expected cube|box|sphere|cylinder|capsule|ellipsoid)");
}

create_object::create_object(std::string type, std::array<double, 3> size, double mass)
: type_name_(to_lower(std::move(type)))
, geom_type_(parse_type(type_name_))
, size_(size)
, mass_(mass)
{
  if (mass_ <= 0.0) {
    throw std::invalid_argument("create_object: mass must be > 0");
  }
  if (size_[0] <= 0.0) {
    throw std::invalid_argument("create_object: size must be > 0");
  }
  // Expand a single scalar (size[1]/size[2] unused) for sphere-like convenience.
  if (geom_type_ == mjGEOM_SPHERE) {
    size_[1] = 0.0;
    size_[2] = 0.0;
  } else if (size_[1] <= 0.0 && size_[2] <= 0.0) {
    size_[1] = size_[0];
    size_[2] = size_[0];
  }
}

double create_object::spawn_height() const
{
  switch (geom_type_) {
    case mjGEOM_SPHERE:
      return size_[0] + 0.15;
    case mjGEOM_CYLINDER:
    case mjGEOM_CAPSULE:
      return size_[1] + 0.15;
    case mjGEOM_ELLIPSOID:
    case mjGEOM_BOX:
    default:
      return size_[2] + 0.15;
  }
}

mjSpec * create_object::make_spec() const
{
  mjSpec * spec = mj_makeSpec();
  if (spec == nullptr) {
    return nullptr;
  }

  mjs_setString(spec->modelname, "object");

  mjsBody * world = mjs_findBody(spec, "world");
  if (world == nullptr) {
    mj_deleteSpec(spec);
    return nullptr;
  }

  mjsBody * body = mjs_addBody(world, /*def=*/nullptr);
  if (body == nullptr) {
    mj_deleteSpec(spec);
    return nullptr;
  }
  mjs_setName(body->element, "object");
  body->pos[0] = 0.0;
  body->pos[1] = 0.0;
  body->pos[2] = 0.0;

  if (mjs_addFreeJoint(body) == nullptr) {
    mj_deleteSpec(spec);
    return nullptr;
  }

  mjsGeom * geom = mjs_addGeom(body, /*def=*/nullptr);
  if (geom == nullptr) {
    mj_deleteSpec(spec);
    return nullptr;
  }
  mjs_setName(geom->element, "object_geom");
  geom->type = geom_type_;
  geom->size[0] = size_[0];
  geom->size[1] = size_[1];
  geom->size[2] = size_[2];
  geom->mass = mass_;
  // Match sticky palm contact bits (bit0 objects, bit1 flex/floor partners).
  geom->contype = 3;
  geom->conaffinity = 3;
  geom->condim = 3;
  geom->friction[0] = 10.0;
  geom->friction[1] = 1.0;
  geom->friction[2] = 0.5;
  geom->adhesion = 5.0;
  geom->gap = 0.002;
  geom->rgba[0] = 0.85f;
  geom->rgba[1] = 0.25f;
  geom->rgba[2] = 0.20f;
  geom->rgba[3] = 1.0f;

  return spec;
}

}  // namespace xela_sparshskin_sim
