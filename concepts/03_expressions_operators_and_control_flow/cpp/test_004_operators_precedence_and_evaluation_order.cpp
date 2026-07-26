// polyglot-covers:
// - cpp.language.operator-precedence-and-associativity
// - cpp.language.short-circuit-logical-operators
// - cpp.language.overloaded-logical-operators
// - cpp.language.sequenced-before
// - cpp.language.function-argument-order
// - cpp.language.conditional-and-comma-operators

// 跨语言迁移提示：内置 && / || 返回 bool，但重载版本不再短路；Python 和 JavaScript
// 的 and / or、&& / || 会返回被选中的操作数。三者也不能互相套用函数实参求值顺序。

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <string>
#include <vector>

namespace {

bool record_condition(std::vector<std::string>& events, std::string name, bool result) {
  events.push_back(std::move(name));
  return result;
}

int record_integer(std::vector<int>& events, int value) {
  events.push_back(value);
  return value;
}

int record_assignment_index(std::vector<std::string>& events) {
  events.push_back("left index");
  return 0;
}

int record_assignment_value(std::vector<std::string>& events) {
  events.push_back("right value");
  return 29;
}

struct LogicalToken {
  bool value;
  std::vector<std::string>* events;
};

LogicalToken make_token(
    std::vector<std::string>& events,
    std::string name,
    bool value) {
  events.push_back(std::move(name));
  return LogicalToken{value, &events};
}

LogicalToken operator&&(LogicalToken left, LogicalToken right) {
  left.events->push_back("operator&&");
  return LogicalToken{left.value && right.value, left.events};
}

TEST(Operators, PrecedenceGroupsOperandsButDoesNotDescribeEvaluationTime) {
  EXPECT_EQ(2 + 3 * 4, 14);
  EXPECT_EQ((2 + 3) * 4, 20);

  int first = 0;
  int second = 0;
  int third = 0;
  first = second = third = 7;

  EXPECT_EQ(first, 7);
  EXPECT_EQ(second, 7);
  EXPECT_EQ(third, 7);

  // 乘法优先级高于加法，赋值按右结合方式分组；这些是语法分组规则。操作数何时
  // 求值由 sequencing 规则另行决定，不能从优先级表推导副作用发生顺序。
}

TEST(Operators, BuiltInLogicalOperatorsShortCircuitTheRightOperand) {
  std::vector<std::string> events;

  bool and_result =
      record_condition(events, "and left", false) &&
      record_condition(events, "and right", true);
  EXPECT_FALSE(and_result);
  EXPECT_EQ(events, (std::vector<std::string>{"and left"}));

  events.clear();
  bool or_result =
      record_condition(events, "or left", true) ||
      record_condition(events, "or right", false);
  EXPECT_TRUE(or_result);
  EXPECT_EQ(events, (std::vector<std::string>{"or left"}));

  // 内建 && 和 || 先求左侧；结果已经确定时右侧完全不求值。常用的空指针保护和
  // 条件式调用依赖这个保证，但右侧副作用也可能因此根本不发生。
}

TEST(Operators, OverloadedLogicalOperatorsDoNotProvideShortCircuiting) {
  std::vector<std::string> events;

  LogicalToken result =
      make_token(events, "left token", false) &&
      make_token(events, "right token", true);

  EXPECT_FALSE(result.value);
  EXPECT_NE(std::find(events.begin(), events.end(), "left token"), events.end());
  EXPECT_NE(std::find(events.begin(), events.end(), "right token"), events.end());
  ASSERT_FALSE(events.empty());
  EXPECT_EQ(events.back(), "operator&&");

  // 重载运算符本质上是函数调用：调用 operator&& 前两个实参都必须求值，因此无法
  // 复制内建 && 的“跳过右侧”语义。库类型重载逻辑运算符时尤其容易制造误解。
}

TEST(EvaluationOrder, AssignmentEvaluatesTheRightOperandBeforeTheLeft) {
  std::vector<std::string> events;
  std::array<int, 1> target{};

  target[record_assignment_index(events)] = record_assignment_value(events);

  EXPECT_EQ(target[0], 29);
  EXPECT_EQ(events, (std::vector<std::string>{"right value", "left index"}));

  // C++17 起，赋值右操作数 sequenced before 左操作数。这里先计算要写入的值，
  // 再计算下标；这不是由赋值运算符的右结合性推导出来的。
}

TEST(EvaluationOrder, BracedInitializerClausesRunFromLeftToRight) {
  std::vector<int> events;

  std::array<int, 3> values{
      record_integer(events, 1),
      record_integer(events, 2),
      record_integer(events, 3),
  };

  EXPECT_EQ(values, (std::array<int, 3>{1, 2, 3}));
  EXPECT_EQ(events, (std::vector<int>{1, 2, 3}));

  // 花括号中的 initializer-clause 按出现顺序求值。需要确定顺序收集多个结果时，
  // 列表初始化比普通函数实参列表提供更强的顺序保证。
}

TEST(EvaluationOrder, FunctionArgumentsAreEvaluatedButTheirOrderIsUnspecified) {
  std::vector<int> events;

  auto receive = [](int left, int right) { return std::array<int, 2>{left, right}; };
  auto values = receive(record_integer(events, 1), record_integer(events, 2));

  EXPECT_EQ(values[0] + values[1], 3);
  ASSERT_EQ(events.size(), 2U);

  std::sort(events.begin(), events.end());
  EXPECT_EQ(events, (std::vector<int>{1, 2}));

  // C++17 起两个实参求值不会彼此交错，但谁先谁后仍未指定。测试只能断言两者都
  // 发生，不能把当前 GCC 常见的从右向左结果写成跨实现保证。
}

TEST(Operators, ConditionalAndCommaOperatorsProvideExplicitSequencing) {
  std::vector<std::string> events;

  int selected = record_condition(events, "condition", true)
                     ? record_assignment_value(events)
                     : record_assignment_index(events);
  EXPECT_EQ(selected, 29);
  EXPECT_EQ(events, (std::vector<std::string>{"condition", "right value"}));

  int counter = 0;
  int comma_result = (++counter, counter += 4, counter * 2);
  EXPECT_EQ(counter, 5);
  EXPECT_EQ(comma_result, 10);

  // ?: 只求被选择的分支；内建逗号运算符保证左表达式先于右表达式。函数实参之间
  // 的逗号只是语法分隔符，不具有逗号运算符的顺序保证。
}

TEST(Operators, ChainedComparisonsDoNotMeanMathematicalRanges) {
  int value = 20;
  bool first_comparison = 0 < value;
  bool chained_meaning = static_cast<int>(first_comparison) < 10;

  EXPECT_TRUE(first_comparison);
  EXPECT_TRUE(chained_meaning);
  EXPECT_FALSE(value < 10);

  // `0 < value < 10` 按 `(0 < value) < 10` 分组：第一次比较得到 bool，再转换成
  // 0 或 1 与 10 比较，所以几乎总为 true。范围判断必须写成 0 < value && value < 10。
}

}  // namespace
