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

int initialize_once(std::vector<std::string>& events) {
  static int value = [&events] {
    events.push_back("initialize");
    return 42;
  }();
  return value;
}

TEST(ModuleInitializationConcept, FunctionLocalStaticInitializesOnce) {
  std::vector<std::string> events;

  EXPECT_EQ(initialize_once(events), 42);
  EXPECT_EQ(initialize_once(events), 42);
  EXPECT_EQ(events, (std::vector<std::string>{"initialize"}));
}

TEST(ModuleInitializationConcept, StaticInitializationOrderAcrossUnitsNeedsCare) {
  // 同一 translation unit 内按定义顺序初始化；跨 translation unit 的动态初始化顺序
  // 可能未指定。函数局部 static 可把依赖推迟到首次调用。
  SUCCEED();
}

TEST(ModuleInitializationConcept, HeaderGuardsPreventTextualRedefinitionOnly) {
  // include guard/pragma once 不建立 Python/Node 模块缓存；链接仍受 ODR 约束。
  SUCCEED();
}

TEST(ModuleInitializationConcept, StandardCppHasNoRuntimeImportByString) {
  // shared-library loading 属于平台 API；C++20 module import 在编译期解析，不能等同 dynamic import。
  SUCCEED();
}

}  // namespace

