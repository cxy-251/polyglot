cmake_minimum_required(VERSION 3.22)

project(polyglot_cpp_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)

set(
  POLYGLOT_GTEST_SOURCE
  "/home/openharmony/third_party/googletest"
  CACHE PATH
  "Path to the GoogleTest source tree supplied by the ohdev container"
)

if(NOT EXISTS "${POLYGLOT_GTEST_SOURCE}/CMakeLists.txt")
  message(FATAL_ERROR "GoogleTest source not found: ${POLYGLOT_GTEST_SOURCE}")
endif()

# GoogleTest 来自 ohdev 的 OpenHarmony 工作区。它只在 /tmp 构建，不复制进本仓库，
# 也不让普通测试运行依赖网络下载。
set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
add_subdirectory(
  "${POLYGLOT_GTEST_SOURCE}"
  "${CMAKE_BINARY_DIR}/_deps/googletest-build"
  EXCLUDE_FROM_ALL
)

include(GoogleTest)

file(
  GLOB_RECURSE POLYGLOT_CPP_TEST_SOURCES
  CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/test_[0-9][0-9][0-9]_*.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/*/test_[0-9][0-9][0-9]_*.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/*/*/test_[0-9][0-9][0-9]_*.cpp"
)

if(NOT POLYGLOT_CPP_TEST_SOURCES)
  message(FATAL_ERROR "No C++ test_NNN_topic.cpp files were found")
endif()

foreach(test_source IN LISTS POLYGLOT_CPP_TEST_SOURCES)
  get_filename_component(test_target "${test_source}" NAME_WE)

  add_executable("${test_target}" "${test_source}")
  target_link_libraries("${test_target}" PRIVATE GTest::gtest_main)

  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(
      "${test_target}"
      PRIVATE
      -Wall
      -Wextra
      -Wpedantic
      -Werror
    )
  endif()

  gtest_discover_tests(
    "${test_target}"
    TEST_PREFIX "${test_target}::"
    DISCOVERY_TIMEOUT 30
  )
endforeach()
