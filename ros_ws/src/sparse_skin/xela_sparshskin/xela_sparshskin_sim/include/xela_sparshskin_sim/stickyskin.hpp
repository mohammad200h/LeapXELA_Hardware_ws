#ifndef XELA_SPARSHSKIN_SIM__STICKYSKIN_HPP_
#define XELA_SPARSHSKIN_SIM__STICKYSKIN_HPP_

#include <mujoco/mujoco.h>

#include <string>

namespace xela_sparshskin_sim
{

struct StickySkinParams
{
  // Adhesive contact force (N) applied to palm flex vertex geoms.
  double adhesion{5.0};
  // Keep contacts active slightly outside the surface for adhesion-at-distance.
  double gap{0.002};
  // Sphere radius for sticky geoms on flex_uspa46_* vertex bodies.
  double radius{0.0006};
};

// Parse an MJCF path into an mjSpec, then make palm flexes named flex_uspa46_*
// sticky by attaching adhesive sphere geoms to each of their vertex bodies.
// Caller owns the returned spec and must free it with mj_deleteSpec.
// On failure returns nullptr and fills error (if non-null).
mjSpec * make_sticky_skin_spec(
  const std::string & xml_path,
  const StickySkinParams & params = StickySkinParams{},
  char * error = nullptr,
  int error_sz = 0);

}  // namespace xela_sparshskin_sim

#endif  // XELA_SPARSHSKIN_SIM__STICKYSKIN_HPP_
