#ifndef OBJESTS_DESCRIPTION__OBJECT_H_
#define OBJESTS_DESCRIPTION__OBJECT_H_

#include <mujoco/mujoco.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ObjectParams
{
  /* MuJoCo geom type: mjGEOM_BOX, SPHERE, CYLINDER, CAPSULE, ELLIPSOID. */
  int type;
  /* Type-specific size (box half-extents; sphere radius in size[0]; etc.). */
  double size[3];
  /* Slide, roll, spin friction. */
  double friction[3];
  /* Adhesive contact force (N). */
  double adhesion;
  double mass;
  double gap;
} ObjectParams;

/* Fill params with defaults (box, high friction, adhesion). */
void object_params_default(ObjectParams * params);

/* Parse --object-type, --size, --friction, --adhesion from argv.
 * Returns 0 on success, non-zero on parse error. */
int object_params_parse_args(int argc, const char ** argv, ObjectParams * params);

/* Human-readable type name for logging. */
const char * object_type_name(int type);

/* Suggested spawn height so the object rests above the plane. */
double object_spawn_height(const ObjectParams * params);

/* Build an mjSpec with a free-jointed body named "object".
 * Caller owns the returned spec and must free it with mj_deleteSpec. */
mjSpec * get_object_spec(const ObjectParams * params);

#ifdef __cplusplus
}
#endif

#endif  /* OBJESTS_DESCRIPTION__OBJECT_H_ */
