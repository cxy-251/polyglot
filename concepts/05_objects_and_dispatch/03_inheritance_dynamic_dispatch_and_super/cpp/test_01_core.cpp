// 继承、动态分派与 super。
// 共同问题：覆盖方法如何动态选择；基类实现如何调用；多继承顺序如何确定；
// 把派生对象当基类使用是否丢失动态类型。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: inheritance_dynamic_dispatch_and_super
// polyglot-related: languages/cpp/language/test_009_inheritance_virtual_dispatch_and_rtti.cpp

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <type_traits>

namespace {

class Base {
 public:
  virtual ~Base() = default;
  virtual std::string describe() const { return "base"; }
};

class Derived final : public Base {
 public:
  std::string describe() const override { return "derived>" + Base::describe(); }
};

TEST(InheritanceDispatchConcept, VirtualCallUsesDynamicObjectType) {
  Derived derived;
  Base& base = derived;

  EXPECT_EQ(base.describe(), "derived>base");
}

TEST(InheritanceDispatchConcept, QualifiedBaseCallBypassesVirtualDispatch) {
  Derived derived;

  EXPECT_EQ(derived.Base::describe(), "base");
}

TEST(InheritanceDispatchConcept, ValueCopyIntoBaseSlicesDerivedState) {
  Derived derived;
  Base sliced = derived;

  EXPECT_EQ(sliced.describe(), "base");

  // Python/JavaScript 的对象引用不会发生这种值切片；C++ 多态对象通常经引用或指针传递。
}

TEST(InheritanceDispatchConcept, RttiCanRecoverDynamicTypeAtRuntime) {
  auto value = std::make_unique<Derived>();
  Base* base = value.get();

  EXPECT_NE(dynamic_cast<Derived*>(base), nullptr);
  EXPECT_EQ(dynamic_cast<Base*>(base), base);
}

TEST(InheritanceDispatchConcept, OverrideContractIsCheckedAtCompileTime) {
  static_assert(std::has_virtual_destructor_v<Base>);
  static_assert(std::is_base_of_v<Base, Derived>);
}

}  // namespace
