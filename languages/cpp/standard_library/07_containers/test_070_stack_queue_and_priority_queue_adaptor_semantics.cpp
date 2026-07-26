// polyglot-covers:
// - cpp.stdlib.containers.stack-lifo-and-underlying-container
// - cpp.stdlib.containers.stack-emplace-top-move-before-pop
// - cpp.stdlib.containers.queue-fifo-front-back-and-underlying-container
// - cpp.stdlib.containers.queue-move-before-pop
// - cpp.stdlib.containers.container-adaptors-no-iteration-interface
// - cpp.stdlib.containers.priority-queue-max-heap-and-range-construction
// - cpp.stdlib.containers.priority-queue-comparator-direction-and-custom-priority
// - cpp.stdlib.containers.priority-queue-const-top-and-unstable-equivalent-order
// - cpp.stdlib.containers.container-adaptor-swap-and-comparison

#include <gtest/gtest.h>

#include <concepts>
#include <deque>
#include <functional>
#include <memory>
#include <queue>
#include <ranges>
#include <stack>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct Task {
  std::string name;
  int priority;
};

struct LowerPriorityFirst {
  bool operator()(const Task& left, const Task& right) const {
    return left.priority < right.priority;
  }
};

TEST(Stack, LastPushedElementIsObservedFirst) {
  std::stack<int> values;

  values.push(1);
  values.push(2);
  values.emplace(3);

  EXPECT_EQ(values.top(), 3);
  values.pop();
  EXPECT_EQ(values.top(), 2);
  EXPECT_EQ(values.size(), 2U);

  using DefaultStorage = typename decltype(values)::container_type;
  static_assert(std::same_as<DefaultStorage, std::deque<int>>);

  // stack 是后进先出适配器，默认包装 deque；它只暴露满足栈语义的接口，
  // 不暴露底层 iterator。pop() 要求非空且返回 void，不会把被删值交给调用者。
}

TEST(Stack, EmplaceReturnsTopAndValuesCanBeMovedBeforePop) {
  std::stack<std::unique_ptr<int>, std::vector<std::unique_ptr<int>>> owners;

  auto& seven = owners.emplace(std::make_unique<int>(7));
  EXPECT_EQ(&seven, &owners.top());
  EXPECT_EQ(*seven, 7);
  owners.push(std::make_unique<int>(11));

  EXPECT_EQ(*owners.top(), 11);

  auto released = std::move(owners.top());
  owners.pop();

  EXPECT_EQ(*released, 11);
  EXPECT_EQ(*owners.top(), 7);

  // emplace 返回新 top 的引用；若底层 vector 后续扩容，该引用也会失效，所以本例只在
  // 下一次 push 前检查 seven。选择底层容器会把其失效规则一并带入适配器。
  // top() 在非 const stack 上返回可变引用，因此 move-only 值应先移动出来再 pop。
}

TEST(Queue, FrontAndBackExposeTheTwoEndsOfFirstInFirstOutOrder) {
  std::queue<std::string> messages;

  messages.push("first");
  messages.emplace("second");
  messages.push("third");

  EXPECT_EQ(messages.front(), "first");
  EXPECT_EQ(messages.back(), "third");

  messages.front() = "FIRST";
  messages.back() = "THIRD";
  messages.pop();

  EXPECT_EQ(messages.front(), "second");
  EXPECT_EQ(messages.back(), "THIRD");

  // queue 从 back 入队、从 front 出队；非 const 的 front/back 都返回可变引用。
  // 默认 deque 同时提供 push_back 和 pop_front，vector 因缺少 pop_front 不能作底层容器。
}

TEST(Queue, MoveOnlyValuesMustAlsoBeMovedBeforePop) {
  std::queue<std::unique_ptr<int>> owners;
  owners.emplace(std::make_unique<int>(7));
  owners.emplace(std::make_unique<int>(11));

  auto first = std::move(owners.front());
  owners.pop();

  EXPECT_EQ(*first, 7);
  EXPECT_EQ(*owners.front(), 11);
  EXPECT_EQ(owners.size(), 1U);

  // queue::pop 与 stack::pop 一样只删除，不返回值。先 move front() 再 pop 可以转移
  // 所有权；pop 后继续使用原 front 引用会悬空。
}

TEST(ContainerAdaptors, DeliberatelyDoNotModelRanges) {
  static_assert(!std::ranges::range<std::stack<int>>);
  static_assert(!std::ranges::range<std::queue<int>>);
  static_assert(!std::ranges::range<std::priority_queue<int>>);
  SUCCEED();

  // 适配器隐藏 iterator 是语义约束，不是缺失功能：遍历会允许调用者绕过 LIFO、FIFO
  // 或堆顶规则。需要遍历时应直接选择并拥有底层容器，而不是试图访问受保护成员 c。
}

TEST(PriorityQueue, DefaultComparatorMakesTheLargestElementTheTop) {
  const std::vector<int> input{3, 1, 4, 1, 5};
  std::priority_queue<int> values(input.begin(), input.end());

  std::vector<int> popped;
  while (!values.empty()) {
    popped.push_back(values.top());
    values.pop();
  }

  EXPECT_EQ(popped, (std::vector<int>{5, 4, 3, 1, 1}));

  // 默认 std::less 使最大元素位于 top。范围构造会建立堆；反复 top/pop 得到优先级顺序，
  // 但这不等于底层数组始终完全排序。
}

TEST(PriorityQueue, GreaterReversesThePriorityAndProducesAMinHeap) {
  std::priority_queue<int, std::vector<int>, std::greater<int>> values;
  for (int value : {3, 1, 4, 2}) {
    values.push(value);
  }

  EXPECT_EQ(values.top(), 1);
  values.pop();
  EXPECT_EQ(values.top(), 2);

  // Compare(a,b)==true 表示 a 的优先级排在 b 之后，因此 std::greater 把较小值放到 top。
  // “比较器为 greater”却得到最小堆很容易反直觉，应从 top 所代表的最高优先级理解。
}

TEST(PriorityQueue, CustomComparatorChoosesWhichRecordHasHigherPriority) {
  std::priority_queue<Task, std::vector<Task>, LowerPriorityFirst> tasks;
  tasks.push(Task{"format", 10});
  tasks.push(Task{"compile", 30});
  tasks.emplace(Task{"test", 20});

  EXPECT_EQ(tasks.top().name, "compile");
  tasks.pop();
  EXPECT_EQ(tasks.top().name, "test");

  // 比较器只看 priority，所以相同 priority 的 Task 等价；priority_queue 是不稳定的，
  // 不保证等价项按插入顺序弹出。若需要稳定次序，应把单调序号纳入比较键。
}

TEST(PriorityQueue, TopIsConstToPreventBreakingTheHeapInvariant) {
  std::priority_queue<Task, std::vector<Task>, LowerPriorityFirst> tasks;
  tasks.push(Task{"compile", 30});

  using TopReference = decltype(tasks.top());
  static_assert(std::is_same_v<TopReference, const Task&>);
  EXPECT_EQ(tasks.top().priority, 30);

  // 即使 priority_queue 本身非 const，top() 仍返回 const_reference；若允许原地修改
  // 比较字段，底层堆会失效。更新优先级通常需要 pop 后修改并重新 push。
}

TEST(ContainerAdaptors, SwapAndRelationalComparisonDelegateToStoredState) {
  std::stack<int> first(std::deque<int>{1, 2});
  std::stack<int> second(std::deque<int>{1, 3});

  EXPECT_LT(first, second);
  first.swap(second);

  EXPECT_EQ(first.top(), 3);
  EXPECT_EQ(second.top(), 2);

  // stack/queue 提供基于底层容器的比较与 swap；比较观察整个保存序列，而不只是 top。
  // priority_queue 在 C++20 不提供对应关系比较，因为堆布局不是逻辑有序序列。
}

}  // namespace
