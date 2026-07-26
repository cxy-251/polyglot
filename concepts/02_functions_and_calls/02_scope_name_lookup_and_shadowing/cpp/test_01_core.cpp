// 作用域、名称查找与遮蔽。
// 共同问题：块是否创建作用域；内层绑定如何遮蔽外层名称；函数如何修改外层状态；
// 读取尚未初始化的局部名称在何处失败。
//
// polyglot-family: functions_and_calls
// polyglot-concept: scope_name_lookup_and_shadowing
// polyglot-related: languages/cpp/language/test_002_declarations_scope_linkage_and_storage_duration.cpp
// polyglot-related: languages/cpp/language/test_015_namespaces_using_lookup_and_adl.cpp

#include <gtest/gtest.h>

#include <string>
#include <vector>

namespace {

namespace catalog {

std::string label() {
  return "catalog";
}

struct Item {
  int value;
};

int score(const Item& item) {
  return item.value * 2;
}

}  // namespace catalog

TEST(ScopeLookupConcept, BracesCreateNestedBlockScope) {
  int value = 1;
  {
    int value = 2;
    EXPECT_EQ(value, 2);
  }
  EXPECT_EQ(value, 1);
}

TEST(ScopeLookupConcept, QualificationBypassesLocalShadowing) {
  std::string label = "local";

  EXPECT_EQ(label, "local");
  EXPECT_EQ(catalog::label(), "catalog");
}

TEST(ScopeLookupConcept, ReferenceParameterExplicitlyMutatesCallerState) {
  int state = 1;
  auto update = [](int& target) { target = 2; };

  update(state);

  EXPECT_EQ(state, 2);
}

TEST(ScopeLookupConcept, ArgumentDependentLookupFindsAssociatedNamespace) {
  catalog::Item item{3};

  EXPECT_EQ(score(item), 6);

  // score 未用 catalog:: 限定；ADL 因参数类型关联到 catalog。Python/JavaScript 没有 ADL。
}

TEST(ScopeLookupConcept, LifetimeStartsAfterInitializationCompletes) {
  int outer = 7;
  {
    int inner = outer;
    EXPECT_EQ(inner, 7);
  }

  // 读取未初始化自动对象会产生未定义值或未定义行为；这里不执行该危险路径。
}

}  // namespace
