// polyglot-covers:
// - cpp.language.explicit-template-specialization
// - cpp.language.class-template-partial-specialization
// - cpp.language.partial-specialization-ordering
// - cpp.language.variable-template-specialization
// - cpp.language.function-template-overload-instead-of-partial-specialization
// - cpp.language.specialization-must-precede-first-use

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

template <typename Value>
struct TypeCategory {
  static constexpr std::string_view name = "primary value";
};

template <typename Value>
struct TypeCategory<Value*> {
  static constexpr std::string_view name = "pointer";
};

template <typename Value>
struct TypeCategory<const Value> {
  static constexpr std::string_view name = "top-level const";
};

template <typename Value, std::size_t Size>
struct TypeCategory<Value[Size]> {
  static constexpr std::string_view name = "bounded array";
  static constexpr std::size_t extent = Size;
};

template <>
struct TypeCategory<bool> {
  static constexpr std::string_view name = "explicit bool";
};

template <typename Value>
inline constexpr std::size_t pointer_depth = 0;

template <typename Value>
inline constexpr std::size_t pointer_depth<Value*> = 1 + pointer_depth<Value>;

template <typename Value>
std::string format_value(const Value&) {
  return "generic value";
}

template <typename Value>
std::string format_value(Value* pointer) {
  return pointer == nullptr ? "null pointer" : "pointer value";
}

TEST(Specialization, PrimaryFullAndPartialSpecializationsSelectByPattern) {
  EXPECT_EQ(TypeCategory<int>::name, "primary value");
  EXPECT_EQ(TypeCategory<int*>::name, "pointer");
  EXPECT_EQ(TypeCategory<const int>::name, "top-level const");
  EXPECT_EQ(TypeCategory<bool>::name, "explicit bool");

  // bool 精确使用 full specialization；T* 和 const T 是 partial specialization 模式。
  // specialization 不是运行期 if，而是在形成具体类型时选择最匹配定义。
}

TEST(Specialization, TopLevelConstAndPointerToConstMatchDifferentPatterns) {
  EXPECT_EQ(TypeCategory<const int*>::name, "pointer");
  EXPECT_EQ(TypeCategory<int* const>::name, "top-level const");

  // const int* 的最外层是指针，因此匹配 T*，其中 T=const int；int* const 的最外层
  // 是 const-qualified pointer，因此匹配 const T。读模板模式时应从外向内分解类型。
}

TEST(Specialization, PartialSpecializationCanExtractArrayExtent) {
  using Category = TypeCategory<double[4]>;

  static_assert(Category::extent == 4);
  EXPECT_EQ(Category::name, "bounded array");

  // partial specialization 可从匹配类型中反推出 Size；未知界数组 T[] 是另一个模式，
  // 不会由 T[N] 自动覆盖。更具体 specialization 胜过 primary template。
}

TEST(VariableTemplates, RecursivePartialSpecializationComputesPointerDepth) {
  static_assert(pointer_depth<int> == 0);
  static_assert(pointer_depth<int*> == 1);
  static_assert(pointer_depth<int***> == 3);

  // variable template 也能 partial specialize。每层 T* specialization 去掉一层指针，
  // 直到 primary template 提供递归基例。
}

TEST(FunctionTemplates, OverloadingReplacesUnavailablePartialSpecialization) {
  int value = 7;

  EXPECT_EQ(format_value(value), "generic value");
  EXPECT_EQ(format_value(&value), "pointer value");
  EXPECT_EQ(format_value(static_cast<int*>(nullptr)), "null pointer");

  // 函数模板不能 partial specialize；应增加重载，让函数模板 partial ordering 选择更
  // 专门的参数模式。full specialization 可以写，但不参与重载的方式容易产生意外。
}

TEST(Specialization, DeclarationMustAppearBeforeAUseThatWouldInstantiatePrimary) {
  static_assert(std::is_same_v<decltype(TypeCategory<bool>::name),
                               const std::string_view>);

  // explicit specialization 必须在每个会导致隐式实例化的首次使用之前可见。先实例化
  // primary 再声明 specialization 是 ill-formed，不能依赖链接器替换已经生成的代码。
}

}  // namespace
