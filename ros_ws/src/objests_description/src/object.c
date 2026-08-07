#include "objests_description/object.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void object_params_default(ObjectParams * params)
{
  if (params == NULL) {
    return;
  }
  params->type = mjGEOM_BOX;
  params->size[0] = 0.05;
  params->size[1] = 0.05;
  params->size[2] = 0.05;
  params->friction[0] = 10.0;
  params->friction[1] = 1.0;
  params->friction[2] = 0.5;
  params->adhesion = 5.0;
  params->mass = 0.1;
  params->gap = 0.002;
}

const char * object_type_name(int type)
{
  switch (type) {
    case mjGEOM_BOX: return "box";
    case mjGEOM_SPHERE: return "sphere";
    case mjGEOM_CYLINDER: return "cylinder";
    case mjGEOM_CAPSULE: return "capsule";
    case mjGEOM_ELLIPSOID: return "ellipsoid";
    default: return "unknown";
  }
}

double object_spawn_height(const ObjectParams * params)
{
  if (params == NULL) {
    return 0.5;
  }
  switch (params->type) {
    case mjGEOM_SPHERE:
      return params->size[0] + 0.2;
    case mjGEOM_CYLINDER:
    case mjGEOM_CAPSULE:
      return params->size[1] + 0.2;
    case mjGEOM_ELLIPSOID:
    case mjGEOM_BOX:
    default:
      return params->size[2] + 0.2;
  }
}

static int parse_doubles(const char * text, double * out, int max_count, int * got)
{
  char * buf = strdup(text);
  if (buf == NULL) {
    return -1;
  }

  int n = 0;
  char * saveptr = NULL;
  for (char * tok = strtok_r(buf, " ,", &saveptr);
    tok != NULL && n < max_count;
    tok = strtok_r(NULL, " ,", &saveptr))
  {
    char * end = NULL;
    out[n] = strtod(tok, &end);
    if (end == tok || *end != '\0') {
      free(buf);
      return -1;
    }
    n++;
  }
  free(buf);
  if (got != NULL) {
    *got = n;
  }
  return n > 0 ? 0 : -1;
}

static int parse_object_type(const char * text, int * type_out)
{
  if (strcmp(text, "box") == 0 || strcmp(text, "cube") == 0) {
    *type_out = mjGEOM_BOX;
  } else if (strcmp(text, "sphere") == 0) {
    *type_out = mjGEOM_SPHERE;
  } else if (strcmp(text, "cylinder") == 0) {
    *type_out = mjGEOM_CYLINDER;
  } else if (strcmp(text, "capsule") == 0) {
    *type_out = mjGEOM_CAPSULE;
  } else if (strcmp(text, "ellipsoid") == 0) {
    *type_out = mjGEOM_ELLIPSOID;
  } else {
    return -1;
  }
  return 0;
}

int object_params_parse_args(int argc, const char ** argv, ObjectParams * params)
{
  if (params == NULL) {
    return -1;
  }

  for (int i = 1; i < argc; ++i) {
    const char * arg = argv[i];
    if (arg == NULL) {
      continue;
    }

    if (strcmp(arg, "--object-type") == 0 || strcmp(arg, "--type") == 0) {
      if (i + 1 >= argc || parse_object_type(argv[++i], &params->type) != 0) {
        fprintf(stderr, "Invalid --object-type (box|sphere|cylinder|capsule|ellipsoid)\n");
        return -1;
      }
    } else if (strcmp(arg, "--size") == 0) {
      if (i + 1 >= argc) {
        fprintf(stderr, "Missing value for --size\n");
        return -1;
      }
      double vals[3] = {0};
      int got = 0;
      if (parse_doubles(argv[++i], vals, 3, &got) != 0) {
        fprintf(stderr, "Invalid --size (expected 1 or 3 floats)\n");
        return -1;
      }
      if (got == 1) {
        params->size[0] = vals[0];
        params->size[1] = vals[0];
        params->size[2] = vals[0];
      } else if (got == 3) {
        params->size[0] = vals[0];
        params->size[1] = vals[1];
        params->size[2] = vals[2];
      } else {
        fprintf(stderr, "Invalid --size (expected 1 or 3 floats)\n");
        return -1;
      }
    } else if (strcmp(arg, "--friction") == 0) {
      if (i + 1 >= argc) {
        fprintf(stderr, "Missing value for --friction\n");
        return -1;
      }
      double vals[3] = {0};
      int got = 0;
      if (parse_doubles(argv[++i], vals, 3, &got) != 0 || (got != 1 && got != 3)) {
        fprintf(stderr, "Invalid --friction (expected 1 or 3 floats: slide[, roll, spin])\n");
        return -1;
      }
      if (got == 1) {
        params->friction[0] = vals[0];
        params->friction[1] = vals[0];
        params->friction[2] = vals[0];
      } else {
        params->friction[0] = vals[0];
        params->friction[1] = vals[1];
        params->friction[2] = vals[2];
      }
    } else if (strcmp(arg, "--adhesion") == 0) {
      if (i + 1 >= argc) {
        fprintf(stderr, "Missing value for --adhesion\n");
        return -1;
      }
      char * end = NULL;
      params->adhesion = strtod(argv[++i], &end);
      if (end == argv[i] || *end != '\0') {
        fprintf(stderr, "Invalid --adhesion\n");
        return -1;
      }
    }
  }

  return 0;
}

mjSpec * get_object_spec(const ObjectParams * params)
{
  ObjectParams local;
  if (params == NULL) {
    object_params_default(&local);
    params = &local;
  }

  mjSpec * spec = mj_makeSpec();
  if (spec == NULL) {
    return NULL;
  }

  mjs_setString(spec->modelname, "object");

  mjsBody * world = mjs_findBody(spec, "world");
  if (world == NULL) {
    mj_deleteSpec(spec);
    return NULL;
  }

  mjsBody * body = mjs_addBody(world, NULL);
  if (body == NULL) {
    mj_deleteSpec(spec);
    return NULL;
  }
  mjs_setName(body->element, "object");
  body->pos[0] = 0.0;
  body->pos[1] = 0.0;
  body->pos[2] = 0.0;

  if (mjs_addFreeJoint(body) == NULL) {
    mj_deleteSpec(spec);
    return NULL;
  }

  mjsGeom * geom = mjs_addGeom(body, NULL);
  if (geom == NULL) {
    mj_deleteSpec(spec);
    return NULL;
  }
  mjs_setName(geom->element, "object_geom");
  geom->type = params->type;
  geom->size[0] = params->size[0];
  geom->size[1] = params->size[1];
  geom->size[2] = params->size[2];
  geom->mass = params->mass;
  geom->friction[0] = params->friction[0];
  geom->friction[1] = params->friction[1];
  geom->friction[2] = params->friction[2];
  geom->adhesion = params->adhesion;
  geom->gap = params->gap;
  geom->rgba[0] = 0.85f;
  geom->rgba[1] = 0.25f;
  geom->rgba[2] = 0.20f;
  geom->rgba[3] = 1.0f;

  return spec;
}
