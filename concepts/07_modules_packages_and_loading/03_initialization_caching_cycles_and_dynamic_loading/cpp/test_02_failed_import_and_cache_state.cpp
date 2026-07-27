// 失败初始化、缓存状态与重试。
// 共同问题：初始化失败的模块是否留在缓存；同一键再次加载是否重新执行；
// 循环依赖为何可能只看到部分初始化状态。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include "support/initialization_fixture.hpp"

namespace {

TEST(TranslationUnitInitializationConcept, LinkedDefinitionInitializesOnceBeforeTestsRun) {
  const void* first = initialization_fixture::state_address();
  const void* second = initialization_fixture::state_address();

  EXPECT_EQ(initialization_fixture::construction_count(), 1);
  EXPECT_EQ(first, second);
}

TEST(TranslationUnitInitializationConcept, RuntimeModuleCacheAnalogyDoesNotApply) {
  EXPECT_EQ(initialization_fixture::construction_count(), 1);

  // translation unit 在构建期编译并由链接器组成程序；没有 Python sys.modules 或 Node
  // URL module map 可在失败后删除/重试。跨 translation unit 动态初始化依赖应改用
  // construct-on-first-use，平台 shared-library API 也不属于 C++20 import。
}

}  // namespace
