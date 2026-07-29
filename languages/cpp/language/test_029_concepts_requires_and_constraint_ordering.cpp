// polyglot-covers:
// - cpp.language.concept-definition
// - cpp.language.requires-expression
// - cpp.language.requires-clause
// - cpp.language.abbreviated-function-template
// - cpp.language.constraint-normalization
// - cpp.language.constraint-subsumption
// - cpp.language.constraint-semantic-requirements

#include <gtest/gtest.h>

#include <concepts>
#include <cstddef>
#include <iterator>
#include <list>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <typename Value>
concept Numeric = std::integral<Value> || std::floating_point<Value>;

template <typename Range>
concept ReadableRange = requires(Range& range, const Range& constant_range) {
  typename Range::value_type;
  { range.begin() } -> std::input_or_output_iterator;
  { constant_range.size() } -> std::convertible_to<std::size_t>;
  requires std::same_as<
      std::remove_cvref_t<decltype(*range.begin())>,
      typename Range::value_type>;
};

template <Numeric Value>
Value square(Value value) {
  return value * value;
}

auto range_size(const ReadableRange auto& range) {
  return range.size();
}

template <typename Value>
std::string number_kind(Value)
  requires std::integral<Value>
{
  return "integral";
}

template <typename Value>
std::string number_kind(Value)
  requires std::signed_integral<Value>
{
  return "signed integral";
}

template <typename Value>
inline constexpr bool can_meow_v = false;

template <typename Value>
inline constexpr bool is_cat_v = false;

struct Cat {};

template <>
inline constexpr bool can_meow_v<Cat> = true;

template <>
inline constexpr bool is_cat_v<Cat> = true;

template <typename Value>
concept Meowable = can_meow_v<Value>;

template <typename Value>
concept GoodMeowableCat = Meowable<Value> && is_cat_v<Value>;

template <Meowable Value>
std::string classify(const Value&) {
  return "meowable";
}

template <GoodMeowableCat Value>
std::string classify(const Value&) {
  return "cat";
}

template <typename Value>
concept HasUnsignedDifference = requires {
  typename Value::difference_type;
  requires std::unsigned_integral<typename Value::difference_type>;
};

struct CounterLike {
  using difference_type = unsigned int;
};

TEST(Concepts, NamedConceptCombinesReusableBooleanConstraints) {
  static_assert(Numeric<int>);
  static_assert(Numeric<double>);
  static_assert(!Numeric<std::string>);
  EXPECT_EQ(square(5), 25);
  EXPECT_DOUBLE_EQ(square(1.5), 2.25);

  // concept 是编译期谓词，不产生新类型。约束失败会让候选不可行，并给出比深层模板
  // 实例化更接近调用点的诊断；它不是运行期输入校验。
}

TEST(RequiresExpression, ChecksTypesExpressionsReturnConstraintsAndNestedRules) {
  static_assert(ReadableRange<std::vector<int>>);
  static_assert(ReadableRange<std::list<std::string>>);
  static_assert(!ReadableRange<int>);

  const std::vector<int> values{1, 2, 3};
  EXPECT_EQ(range_size(values), 3U);

  // 四种 requirement 分别是 type、simple、compound 和 nested requirement。
  // requires-expression 遇到无效表达式会得到 false，而不是执行 begin() 或 size()。
}

TEST(ConstraintOrdering, MoreConstrainedOverloadWinsBySubsumption) {
  EXPECT_EQ(number_kind(7), "signed integral");
  EXPECT_EQ(number_kind(7U), "integral");
  EXPECT_EQ(classify(Cat{}), "cat");

  // signed_integral 的定义复用了 integral，因此规范化后的原子约束能建立 subsumption。
  // GoodMeowableCat 同样复用 Meowable；若直接重复写 can_meow_v<T>，文本相似的表达式
  // 也可能成为不同原子约束，使两个重载无法排序。
}

TEST(RequiresClause, CanReferToDependentTypesWithoutTriggeringAHardError) {
  static_assert(HasUnsignedDifference<CounterLike>);
  static_assert(!HasUnsignedDifference<int>);
  static_assert(!HasUnsignedDifference<std::vector<int>>);

  // requirement 按词法顺序检查，前面的 type requirement 失败后不会继续形成后面的嵌套
  // 类型。这种短路使“没有 difference_type”成为 false，而不是 hard error。
}

TEST(ConceptSemantics, CompilerChecksSyntaxButSomeMeaningRemainsAContract) {
  static_assert(std::copyable<int>);

  // 标准 concept 常含 equality-preserving、稳定性或复杂度等语义要求，编译器通常只能
  // 检查表达式是否存在和类型是否匹配。谎报 operator== 语义仍可能通过语法约束，随后
  // 让依赖该契约的算法行为不可靠。
}

}  // namespace
