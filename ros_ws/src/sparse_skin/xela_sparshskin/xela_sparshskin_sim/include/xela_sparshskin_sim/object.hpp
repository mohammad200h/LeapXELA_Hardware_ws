#ifndef XELA_SPARSHSKIN_SIM__OBJECT_HPP_
#define XELA_SPARSHSKIN_SIM__OBJECT_HPP_

#include <mujoco/mujoco.h>

#include <array>
#include <string>

namespace xela_sparshskin_sim
{

// Builds a free-jointed MuJoCo object as an mjSpec.
// Default: cube (box) with 5 cm half-extents and mass 0.1 kg.
class create_object
{
public:
  // type: "cube"/"box", "sphere", "cylinder", "capsule", "ellipsoid"
  // size: type-specific MuJoCo geom sizes (box = half-extents).
  explicit create_object(
    std::string type = "cube",
    std::array<double, 3> size = {0.025, 0.025, 0.025},
    double mass = 0.1);

  // Caller owns the returned spec and must free it with mj_deleteSpec.
  // Returns nullptr on failure.
  mjSpec * make_spec() const;

  mjtGeom geom_type() const { return geom_type_; }
  const std::array<double, 3> & size() const { return size_; }
  double mass() const { return mass_; }
  const std::string & type_name() const { return type_name_; }

  // Suggested spawn height so the object starts clear of the floor.
  double spawn_height() const;

private:
  static mjtGeom parse_type(const std::string & type);

  std::string type_name_;
  mjtGeom geom_type_;
  std::array<double, 3> size_;
  double mass_;
};

}  // namespace xela_sparshskin_sim

#endif  // XELA_SPARSHSKIN_SIM__OBJECT_HPP_
