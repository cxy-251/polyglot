// 初始化、缓存、循环依赖与动态加载。
// 共同问题：模块初始化执行几次；缓存键是什么；循环导入看到什么状态；
// 运行期加载如何报告失败。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include <string>
#include <vector>

namespace {

template <typename Tag>
int initialize_once(std::vector<std::string>& events) {
  static int value = [&events] {
    events.push_back("initialize");
    return 42;
  }();
  return value;
}

TEST(ModuleInitializationConcept, FunctionLocalStaticInitializesOnce) {
  struct CoreInitialization;
  std::vector<std::string> events;

  EXPECT_EQ(initialize_once<CoreInitialization>(events), 42);
  EXPECT_EQ(initialize_once<CoreInitialization>(events), 42);
  EXPECT_EQ(events, (std::vector<std::string>{"initialize"}));
}

TEST(ModuleInitializationConcept, StaticInitializationOrderAcrossUnitsNeedsCare) {
  std::vector<std::string> events;
  auto dependency = [&events] {
    static const int value = [&events] {
      events.push_back("dependency");
      return 7;
    }();
    return value;
  };

  EXPECT_EQ(dependency(), 7);
  EXPECT_EQ(dependency(), 7);
  EXPECT_EQ(events, (std::vector<std::string>{"dependency"}));

  // 同一 translation unit 内按定义顺序初始化；跨 translation unit 的动态初始化顺序
  // 可能未指定。函数局部 static 可把依赖推迟到首次调用。
}

TEST(ModuleInitializationConcept, HeaderGuardsPreventTextualRedefinitionOnly) {
  struct HeaderInitialization;
  std::vector<std::string> events;

  static_assert(__cplusplus >= 202002L);
  EXPECT_EQ(initialize_once<HeaderInitialization>(events), 42);
  EXPECT_EQ(events, (std::vector<std::string>{"initialize"}));

  // include guard/pragma once 不建立 Python/Node 模块缓存；链接仍受 ODR 约束。
}

}  // namespace
