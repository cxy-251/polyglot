// polyglot-covers:
// - cpp.language.translation-units
// - cpp.language.one-definition-rule
// - cpp.language.inline-functions-variables-and-local-statics
// - cpp.language.internal-and-external-linkage-across-translation-units
// - cpp.language.module-declaration-export-import-and-reachability
// - cpp.implementation.gcc11-modules-ts-gap

#include <gtest/gtest.h>

#include "support/support_020_odr.hpp"

namespace {

TEST(TranslationUnits, HeaderConstWithInternalLinkageCreatesSeparateObjects) {
  const int* from_a = odr_examples::internal_address_from_a();
  const int* from_b = odr_examples::internal_address_from_b();

  EXPECT_EQ(*from_a, 7);
  EXPECT_EQ(*from_b, 7);
  EXPECT_NE(from_a, from_b);

  // support_020_odr.hpp 被主测试和两个 support .cpp 分别包含。namespace 作用域普通
  // const 具有内部链接，所以每个翻译单元都有独立对象；值相同不表示实体相同。
}

TEST(OneDefinitionRule, InlineVariableDenotesOneObjectAcrossTranslationUnits) {
  int* from_a = odr_examples::inline_address_from_a();
  int* from_b = odr_examples::inline_address_from_b();

  EXPECT_EQ(from_a, from_b);
  EXPECT_EQ(from_a, &odr_examples::inline_object);

  *from_a = 43;
  EXPECT_EQ(odr_examples::inline_object, 43);
  odr_examples::inline_object = 41;

  // inline 允许在多个翻译单元提供相同定义，并要求它们共同表示一个具有统一地址的
  // 实体。定义不一致仍违反 ODR，链接器不保证能够诊断这种 ill-formed NDR 程序。
}

TEST(OneDefinitionRule, StaticInsideInlineFunctionIsAlsoOneSharedObject) {
  int* from_a = odr_examples::function_static_address_from_a();
  int* from_b = odr_examples::function_static_address_from_b();

  EXPECT_EQ(from_a, from_b);
  EXPECT_EQ(from_a, &odr_examples::inline_function_static());

  *from_b = 19;
  EXPECT_EQ(odr_examples::inline_function_static(), 19);
  odr_examples::inline_function_static() = 17;

  // 具有外部链接的 inline 函数在各翻译单元共享一个 function-local static，不能把
  // 头文件中看到的多份函数定义误认为多份单例状态。
}

TEST(TranslationUnits, ExternDeclarationRefersToOneOutOfLineDefinition) {
  int* from_a = odr_examples::external_address_from_a();
  int* from_b = odr_examples::external_address_from_b();

  EXPECT_EQ(from_a, from_b);
  EXPECT_EQ(*from_a, 23);

  // 头文件只给 external_object 提供 extern 声明，support A 提供唯一非 inline 定义，
  // support B 和主测试都引用该实体。缺少定义或重复定义通常在链接阶段暴露。
}

TEST(Modules, BaselineRecordsTheUnavailableStandardModuleWorkflow) {
#if defined(__cpp_modules)
  EXPECT_GE(__cpp_modules, 201907L);
#else
  GTEST_SKIP()
      << "GCC 11.4 baseline does not enable standard modules without -fmodules-ts";
#endif

  // C++20 module unit 以 `export module name;` 建立模块接口，import 只看到导出的声明；
  // global module fragment 可先包含传统头文件，private fragment 隔离仅本单元实现。
  // 模块中的名字仍受 ODR、可达性和所有权规则约束，宏不会像头文件那样随 import 传播。
  // 当前 GCC 11.4 的实现是实验性 Modules TS，CMake 3.22 也没有稳定依赖扫描，因此
  // 本仓库明确保留此 skip，而不把实验参数伪装成可移植 C++20 验证。
}

}  // namespace
