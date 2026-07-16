// polyglot-covers:
// - cpp.language.selection-and-iteration-statements
// - cpp.language.if-and-switch-init-statements
// - cpp.language.switch-fallthrough
// - cpp.language.break-continue-and-goto
// - cpp.language.range-for-desugaring-and-adl
// - cpp.language.range-for-copy-reference-and-lifetime

#include <gtest/gtest.h>

#include <array>
#include <string>
#include <utility>
#include <vector>

namespace adl_range_example {

struct IntRange {
  std::array<int, 3> values;
};

int* begin(IntRange& range) { return range.values.data(); }
int* end(IntRange& range) { return range.values.data() + range.values.size(); }

}  // namespace adl_range_example

namespace {

enum class ProcessState {
  created,
  running,
  stopped,
};

std::vector<int> make_values() { return {2, 3, 5}; }

TEST(SelectionStatements, InitStatementNamesLiveThroughAllBranches) {
  int branch = 0;

  if (int value = 7; value > 5) {
    branch = value;
  } else {
    branch = -value;
  }

  EXPECT_EQ(branch, 7);

  // init-statement 中的 value 在条件以及 if/else 两个分支都可见，离开整个 if 后销毁。
  // 这适合把锁、查找结果等临时状态限制在控制语句范围内，避免名字泄漏到后续代码。
}

TEST(SelectionStatements, SwitchCanInitializeAndDeliberatelyFallThrough) {
  std::vector<std::string> events;
  ProcessState state = ProcessState::created;

  switch (int attempt = 1; state) {
    case ProcessState::created:
      events.push_back("created " + std::to_string(attempt));
      [[fallthrough]];
    case ProcessState::running:
      events.push_back("active");
      break;
    case ProcessState::stopped:
      events.push_back("stopped");
      break;
  }

  EXPECT_EQ(events, (std::vector<std::string>{"created 1", "active"}));

  // case 标签不会自动形成作用域，跨标签跳过局部对象初始化通常是非法的。需要局部
  // 变量时应给 case 加花括号；有意贯穿则用 [[fallthrough]] 说明不是遗漏 break。
}

TEST(IterationStatements, ContinueAndBreakAffectOnlyTheNearestLoop) {
  std::vector<int> accepted;

  for (int value = 0; value < 10; ++value) {
    if (value % 2 == 0) {
      continue;
    }
    if (value > 6) {
      break;
    }
    accepted.push_back(value);
  }

  EXPECT_EQ(accepted, (std::vector<int>{1, 3, 5}));

  int do_while_runs = 0;
  do {
    ++do_while_runs;
  } while (false);
  EXPECT_EQ(do_while_runs, 1);

  // do-while 在检查条件前执行一次；continue 跳到最近循环的迭代步骤或条件检查，
  // break 只退出最近的循环或 switch，不会自动退出外层循环。
}

TEST(RangeFor, CopyAndReferenceLoopVariablesHaveDifferentEffects) {
  std::vector<int> values{1, 2, 3};

  for (int value : values) {
    value *= 10;
  }
  EXPECT_EQ(values, (std::vector<int>{1, 2, 3}));

  for (int& value : values) {
    value *= 10;
  }
  EXPECT_EQ(values, (std::vector<int>{10, 20, 30}));

  // `auto value` 同样会复制元素，`auto&` 才能修改原元素；只读且元素可能很大时常用
  // `const auto&`。面对代理引用类型时，auto&& 往往比固定的 value_type& 更通用。
}

TEST(RangeFor, AdlFindsFreeBeginAndEndForUserDefinedRanges) {
  adl_range_example::IntRange range{{4, 5, 6}};
  int sum = 0;

  for (int value : range) {
    sum += value;
  }

  EXPECT_EQ(sum, 15);

  // range-for 会保存 range 表达式，然后查找 begin/end。类型没有同时提供成员 begin
  // 和 end 时，会通过 ADL 查找关联命名空间中的自由函数；普通非 ADL 查找不参与。
}

TEST(RangeFor, TheRangeTemporaryLivesUntilTheLoopFinishes) {
  std::vector<int> observed;

  for (int value : make_values()) {
    observed.push_back(value * 2);
  }

  EXPECT_EQ(observed, (std::vector<int>{4, 6, 10}));

  for (std::vector<int> owned{7, 8}; int value : owned) {
    observed.push_back(value);
  }
  EXPECT_EQ(observed, (std::vector<int>{4, 6, 10, 7, 8}));

  // range-for 内部的转发引用会把顶层 range 临时量寿命延长到循环结束。C++20 的
  // init-statement 还能显式持有复杂所有者，避免从函数返回悬空子对象引用的陷阱。
}

TEST(JumpStatements, GotoCannotBypassRequiredObjectInitialization) {
  int visits = 0;

  goto destination;
  ++visits;

destination:
  ++visits;
  EXPECT_EQ(visits, 1);

  // goto 仍是语言的一部分，但不能跳入需要绕过自动对象初始化的作用域。RAII 代码中
  // 通常用结构化控制流；离开作用域的合法跳转仍会析构已经构造的自动对象。
}

}  // namespace
