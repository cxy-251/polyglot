// 模块、导入、链接与绑定可见性。
// 共同问题：模块何时执行；导入得到模块还是值快照；命名空间如何隔离；
// 声明如何跨文件暴露。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include "support/module_fixture.hpp"

namespace {

TEST(ModulesLinkageConcept, HeaderDeclarationRefersToOneExternDefinition) {
  module_fixture::shared_value = 3;

  EXPECT_EQ(module_fixture::shared_value, 3);
  EXPECT_EQ(module_fixture::read_shared(), 3);

  module_fixture::shared_value = 4;
  EXPECT_EQ(module_fixture::read_shared(), 4);
}

TEST(ModulesLinkageConcept, NamespaceQualifiesNamesAcrossTranslationUnits) {
  EXPECT_EQ(module_fixture::doubled(3), 6);
  EXPECT_EQ(module_fixture::initialization_count(), 1);
}

TEST(ModulesLinkageConcept, IncludeIsTextualWhileLinkageJoinsDefinitions) {
  static_assert(module_fixture::doubled(3) == 6);
  EXPECT_EQ(&module_fixture::inline_value, module_fixture::inline_value_address_from_other_unit());

  // 头文件提供声明和 inline 定义；support .cpp 提供一次外部定义并只链接到本主题目标。
}

TEST(ModulesLinkageConcept, ExternalNameIsNotAJavaScriptStyleLiveBinding) {
  module_fixture::shared_value = 4;
  int snapshot = module_fixture::shared_value;
  module_fixture::shared_value = 5;

  EXPECT_EQ(snapshot, 4);
  EXPECT_EQ(module_fixture::shared_value, 5);
}

}  // namespace
