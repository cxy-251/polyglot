// 导入绑定、别名与可变导出对象。
// 共同问题：导入后读取的是源绑定还是本地值；共享对象的内部修改是否可见；
// 重新绑定与修改对象为何产生不同迁移结果。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include "support/module_fixture.hpp"

namespace {

TEST(ModuleBindingConcept, InlineVariableDenotesOneEntityAcrossTranslationUnits) {
  module_fixture::inline_value = 9;

  EXPECT_EQ(module_fixture::inline_value_address_from_other_unit(), &module_fixture::inline_value);
  EXPECT_EQ(*module_fixture::inline_value_address_from_other_unit(), 9);

  // inline variable 可在多个 translation unit 中定义但表示同一实体；这是 ODR/linkage，
  // 不是 JavaScript importer 持有的只读 live binding。
}

TEST(ModuleBindingConcept, ValueCopyAndReferenceAliasObserveDifferentUpdates) {
  module_fixture::shared_value = 3;
  int copied = module_fixture::shared_value;
  int& alias = module_fixture::shared_value;

  module_fixture::shared_value = 5;

  EXPECT_EQ(copied, 3);
  EXPECT_EQ(alias, 5);

  // C++ 使用声明的值类别和引用显式选择复制或别名；include/import 不自动改变该语义。
}

}  // namespace
