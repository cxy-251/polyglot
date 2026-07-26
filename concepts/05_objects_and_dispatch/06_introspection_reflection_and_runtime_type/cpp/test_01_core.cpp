// 自省、反射与运行时类型。
// 共同问题：如何查询真实类型与成员；能否动态读写和调用；反射是否触发用户代码；
// 哪些检查只存在于编译期。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: introspection_reflection_and_runtime_type
// polyglot-related: languages/cpp/language/test_009_inheritance_virtual_dispatch_and_rtti.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <type_traits>
#include <typeinfo>

namespace {

class Base {
 public:
  virtual ~Base() = default;
};

class Derived : public Base {
 public:
  int run(int value) const { return value * 2; }
};

template <typename T>
concept Runnable = requires(const T& value) {
  { value.run(1) } -> std::same_as<int>;
};

TEST(IntrospectionConcept, TypeTraitsAndConceptsInspectTypesAtCompileTime) {
  static_assert(std::is_base_of_v<Base, Derived>);
  static_assert(Runnable<Derived>);
  static_assert(!Runnable<Base>);
}

TEST(IntrospectionConcept, TypeidObservesDynamicTypeForPolymorphicObjects) {
  Derived derived;
  Base& base = derived;

  EXPECT_EQ(typeid(base), typeid(Derived));
  EXPECT_NE(typeid(base), typeid(Base));
}

TEST(IntrospectionConcept, DynamicCastPerformsCheckedRuntimeDowncast) {
  Derived derived;
  Base* base = &derived;

  auto* recovered = dynamic_cast<Derived*>(base);

  ASSERT_NE(recovered, nullptr);
  EXPECT_EQ(recovered->run(3), 6);
}

TEST(IntrospectionConcept, MemberPointerAllowsSelectedDynamicInvocation) {
  Derived derived;
  auto operation = &Derived::run;

  EXPECT_EQ((derived.*operation)(3), 6);

  // C++20 没有按字符串枚举、读取或新增任意成员的标准反射 API。
}

}  // namespace
