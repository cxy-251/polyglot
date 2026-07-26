// polyglot-covers:
// - cpp.language.implicit-template-instantiation
// - cpp.language.explicit-instantiation-declaration
// - cpp.language.explicit-instantiation-definition
// - cpp.language.class-template-explicit-instantiation
// - cpp.language.function-template-explicit-instantiation
// - cpp.language.template-multi-translation-unit

#include <gtest/gtest.h>

#include "support/support_031_explicit_instantiation.hpp"

#include <string>

namespace {

namespace examples = explicit_instantiation_examples;

TEST(TemplateInstantiation, ImplicitInstantiationFormsOnlyTheRequestedSpecialization) {
  examples::Accumulator<std::string> words;
  words.add("poly");
  words.add("glot");

  EXPECT_EQ(words.total(), "polyglot");
  EXPECT_EQ(words.count(), 2U);

  // string 版本未写 explicit instantiation；当前翻译单元在首次需要完整定义时隐式实例化。
  // 模板本身不是可链接实体，每组模板实参形成自己的 specialization。
}

TEST(ExplicitInstantiation, OneDefinitionServesSeveralTranslationUnits) {
  EXPECT_EQ(examples::accumulate_in_a(2, 3), 5);
  EXPECT_EQ(examples::accumulate_in_b(10, 7), 17);
  EXPECT_EQ(examples::twice_in_a(9), 18);
  EXPECT_EQ(examples::twice_in_b(12), 24);

  // 头文件的 extern template 抑制各使用方隐式生成 int 版本；support ... a.cpp 中的
  // template class/function 语句是全程序唯一的 explicit instantiation definition。
}

TEST(ExplicitInstantiation, FunctionSpecializationDenotesOneLinkedEntity) {
  EXPECT_EQ(examples::twice_address_from_a(), examples::twice_address_from_b());

  // 两个翻译单元取得同一函数 specialization 的地址。explicit instantiation 常用于把
  // 常用 specialization 的代码生成集中到一个源文件，以减少构建时间与代码重复。
}

TEST(ExplicitInstantiation, DefinitionStillNeedsTheTemplateDefinitionVisible) {
  examples::Accumulator<int> values;
  values.add(4);
  values.add(6);
  EXPECT_EQ(values.total(), 10);

  // declaration 可只看到模板声明，但 explicit instantiation definition 必须看到模板
  // 定义。extern template 不是预编译二进制保证：若忘记提供 definition，最终会链接失败。
}

}  // namespace
