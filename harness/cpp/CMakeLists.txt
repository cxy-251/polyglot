cmake_minimum_required(VERSION 3.22)

project(polyglot_cpp_harness LANGUAGES CXX)

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

get_filename_component(
  POLYGLOT_REPOSITORY_ROOT
  "${CMAKE_CURRENT_SOURCE_DIR}/../.."
  ABSOLUTE
)
set(POLYGLOT_CPP_COURSE_ROOT "${POLYGLOT_REPOSITORY_ROOT}/languages/cpp")

set(
  POLYGLOT_TEST_LAYER
  "course"
  CACHE STRING
  "Test layer to build: course, concepts, or harness"
)
set_property(CACHE POLYGLOT_TEST_LAYER PROPERTY STRINGS course concepts harness)

if(POLYGLOT_TEST_LAYER STREQUAL "course")
  file(
    GLOB_RECURSE POLYGLOT_CPP_TEST_SOURCES
    CONFIGURE_DEPENDS
    "${POLYGLOT_CPP_COURSE_ROOT}/language/test_[0-9][0-9][0-9]_*.cpp"
    "${POLYGLOT_CPP_COURSE_ROOT}/standard_library/*/test_[0-9][0-9][0-9]_*.cpp"
  )
  file(
    GLOB_RECURSE POLYGLOT_CPP_SUPPORT_SOURCES
    CONFIGURE_DEPENDS
    "${POLYGLOT_CPP_COURSE_ROOT}/language/support/support_*.cpp"
  )
elseif(POLYGLOT_TEST_LAYER STREQUAL "concepts")
  file(
    GLOB_RECURSE POLYGLOT_CPP_TEST_SOURCES
    CONFIGURE_DEPENDS
    "${POLYGLOT_REPOSITORY_ROOT}/concepts/[0-9][0-9]_*/[0-9][0-9]_*/cpp/test_[0-9][0-9]_*.cpp"
  )
  set(POLYGLOT_CPP_SUPPORT_SOURCES)
elseif(POLYGLOT_TEST_LAYER STREQUAL "harness")
  file(
    GLOB POLYGLOT_CPP_TEST_SOURCES
    CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_[0-9][0-9]_*.cpp"
  )
  set(POLYGLOT_CPP_SUPPORT_SOURCES)
else()
  message(FATAL_ERROR "POLYGLOT_TEST_LAYER must be course, concepts, or harness")
endif()

if(NOT POLYGLOT_CPP_TEST_SOURCES)
  message(FATAL_ERROR "No C++ tests were found for layer: ${POLYGLOT_TEST_LAYER}")
endif()

foreach(test_source IN LISTS POLYGLOT_CPP_TEST_SOURCES)
  get_filename_component(test_name "${test_source}" NAME_WE)
  set(test_support_sources)

  if(POLYGLOT_TEST_LAYER STREQUAL "course")
    set(test_target "${test_name}")
    string(REGEX MATCH "^test_([0-9][0-9][0-9])_" test_name_match "${test_target}")
    if(NOT test_name_match)
      message(FATAL_ERROR "Invalid C++ course test name: ${test_target}")
    endif()
    set(test_number "${CMAKE_MATCH_1}")
    set(test_support_sources ${POLYGLOT_CPP_SUPPORT_SOURCES})
    list(FILTER test_support_sources INCLUDE REGEX "support_${test_number}_.+\\.cpp$")
    set(test_labels "polyglot-language")
  elseif(POLYGLOT_TEST_LAYER STREQUAL "concepts")
    get_filename_component(test_language_directory "${test_source}" DIRECTORY)
    get_filename_component(test_topic_directory "${test_language_directory}" DIRECTORY)
    get_filename_component(test_family_directory "${test_topic_directory}" DIRECTORY)
    get_filename_component(test_topic "${test_topic_directory}" NAME)
    get_filename_component(test_family "${test_family_directory}" NAME)
    set(test_target "concept_${test_family}_${test_topic}_${test_name}")
    file(
      GLOB test_support_sources
      CONFIGURE_DEPENDS
      "${test_language_directory}/support/*.cpp"
    )
    set(test_labels "polyglot-concept")
  else()
    set(test_target "harness_${test_name}")
    set(test_labels "polyglot-harness")
  endif()

  add_executable("${test_target}" "${test_source}" ${test_support_sources})
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
    PROPERTIES LABELS "${test_labels}"
  )
endforeach()
