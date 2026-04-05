#project(thirdparty)

if(NOT PLACELOL_CONVERT_ONLY)
  add_subdirectory(flute)
endif()

set(OPENBLAS OFF CACHE BOOL "Turn off OPENBLAS for Limbo")
set(INSTALL_LIMBO OFF CACHE BOOL "Turn off installation for Limbo")
set(GENERATE_DOCS OFF CACHE BOOL "Turn off documentation for Limbo")
set(ENABLE_TEST OFF CACHE BOOL "Turn off test for Limbo")
add_subdirectory(Limbo)
if(NOT PLACELOL_CONVERT_ONLY)
  add_subdirectory(munkres-cpp)
  add_subdirectory(OpenTimer)
endif()

if(NOT PLACELOL_CONVERT_ONLY)
  install(
      DIRECTORY NCTUgr.ICCAD2012 DESTINATION thirdparty
      )
endif()
