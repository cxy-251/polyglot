// polyglot-covers:
// - cpp.language.sfinae-immediate-context
// - cpp.language.expression-sfinae
// - cpp.language.void-t-detection-idiom
// - cpp.language.enable-if
// - cpp.language.declval-unevaluated-operand
// - cpp.language.overload-priority-tag

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <typename Value, typename = void>
struct HasValueType : std::false_type {};

template <typename Value>
struct HasValueType<Value, std::void_t<typename Value::value_type>> : std::true_type {};

template <typename Value>
inline constexpr bool has_value_type_v = HasValueType<Value>::value;

template <typename Value>
auto measured_size(const Value& value) -> decltype(value.size(), std::size_t{}) {
  return value.size();
}

std::size_t measured_size(...) { return 0; }

template <typename Value>
auto doubled(Value value) -> std::enable_if_t<std::is_integral_v<Value>, Value> {
  return value * 2;
}

template <typename Value>
auto doubled(Value value) -> std::enable_if_t<std::is_floating_point_v<Value>, Value> {
  return value * Value{2};
}

template <int Rank>
struct PriorityTag : PriorityTag<Rank - 1> {};

template <>
struct PriorityTag<0> {};

template <typename Value>
auto text_of(const Value& value, PriorityTag<2>) -> decltype(value.to_string()) {
  return value.to_string();
}

template <typename Value>
auto text_of(const Value& value, PriorityTag<1>) -> decltype(std::to_string(value)) {
  return std::to_string(value);
}

template <typename Value>
std::string text_of(const Value&, PriorityTag<0>) {
  return "unprintable";
}

template <typename Value>
std::string text_of(const Value& value) {
  return text_of(value, PriorityTag<2>{});
}

struct MemberFormatted {
  std::string to_string() const { return "member"; }
};

struct Opaque {};

TEST(DetectionIdiom, VoidTTurnsAMissingNestedTypeIntoFalse) {
  static_assert(has_value_type_v<std::vector<int>>);
  static_assert(!has_value_type_v<int>);
  SUCCEED();

  // void_t 的参数若能替换便得到 void，从而选择 partial specialization。若 int 没有
  // value_type，替换失败只移除该候选，不会让整个翻译单元报错。
}

TEST(ExpressionSfinae, InvalidExpressionRemovesOnlyTheTemplateCandidate) {
  const std::vector<int> values{1, 2, 3};

  EXPECT_EQ(measured_size(values), 3U);
  EXPECT_EQ(measured_size(42), 0U);

  // 逗号左侧只检查 value.size() 是否良构，右侧把返回类型固定为 size_t。
  // decltype 是 unevaluated operand，检查期间不会真正调用 size()。
}

TEST(EnableIf, MutuallyExclusiveConditionsPartitionAnOverloadSet) {
  EXPECT_EQ(doubled(6), 12);
  EXPECT_DOUBLE_EQ(doubled(1.25), 2.5);

  // enable_if 条件为 false 时没有 type，返回类型替换失败并移除候选。条件必须互斥；
  // 若多个候选同时成立，SFINAE 不会替开发者决定优先级，调用仍可能 ambiguous。
}

TEST(Declval, FormsExpressionsWithoutConstructingAnObject) {
  using Expression = decltype(std::declval<const std::string&>().size());

  static_assert(std::is_same_v<Expression, std::size_t>);
  static_assert(std::is_same_v<decltype(std::declval<int&&>()), int&&>);
  SUCCEED();

  // declval 只有声明，不能在 evaluated context 调用；它专门在 decltype、requires 等
  // 不求值环境中伪造指定值类别，因而不要求类型可默认构造。
}

TEST(OverloadPriority, TriesCapabilitiesFromMostSpecificToFallback) {
  EXPECT_EQ(text_of(MemberFormatted{}), "member");
  EXPECT_EQ(text_of(17), "17");
  EXPECT_EQ(text_of(Opaque{}), "unprintable");

  // PriorityTag<2> 可隐式转成较低等级。高等级表达式替换失败后，重载解析依次选择
  // 可用的下一等级；这比几个同等地位的 enable_if 重载更明确。
}

TEST(SfinaeBoundary, OnlyFailuresInTheImmediateContextAreSubstitutionFailures) {
  static_assert(!has_value_type_v<Opaque>);
  SUCCEED();

  // SFINAE 只保护函数类型、模板参数等 immediate context。若候选已经选中后，其函数体
  // 实例化才访问不存在的成员，那是普通 hard error，不能期待 fallback 重载接管。
}

}  // namespace
