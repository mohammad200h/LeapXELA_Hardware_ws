# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_xela_models_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED xela_models_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(xela_models_FOUND FALSE)
  elseif(NOT xela_models_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(xela_models_FOUND FALSE)
  endif()
  return()
endif()
set(_xela_models_CONFIG_INCLUDED TRUE)

# output package information
if(NOT xela_models_FIND_QUIETLY)
  message(STATUS "Found xela_models: 1.2.0 (${xela_models_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'xela_models' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${xela_models_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(xela_models_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${xela_models_DIR}/${_extra}")
endforeach()
