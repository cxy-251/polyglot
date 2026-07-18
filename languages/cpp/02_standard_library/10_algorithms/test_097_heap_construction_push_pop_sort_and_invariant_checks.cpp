// polyglot-covers:
// - cpp.stdlib.algorithms.make-heap-root-and-partial-order
// - cpp.stdlib.algorithms.push-heap-appended-element-precondition
// - cpp.stdlib.algorithms.pop-heap-selected-element-at-tail
// - cpp.stdlib.algorithms.sort-heap-consumes-heap-into-order
// - cpp.stdlib.algorithms.is-heap-and-is-heap-until
// - cpp.stdlib.algorithms.heap-comparator-max-versus-min-root
// - cpp.stdlib.algorithms.ranges-heap-projection
// - cpp.stdlib.algorithms.heap-empty-and-singleton-boundaries
// - cpp.stdlib.algorithms.vector-backed-priority-workflow

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <ranges>
#include <string>
#include <vector>

namespace {

TEST(MakeHeap, DefaultLessPlacesAMaximumAtTheRootWithoutFullySorting) {
  std::vector<int> values{3, 1, 6, 5, 2, 4};

  auto end = std::ranges::make_heap(values);

  EXPECT_EQ(end, values.end());
  EXPECT_TRUE(std::ranges::is_heap(values));
  EXPECT_EQ(values.front(), 6);
  EXPECT_FALSE(std::ranges::is_sorted(values));

  // 默认 less 构造 max-heap：front 是最大值，每个父节点不小于其子节点；兄弟和不同
  // 子树之间没有全序保证，因此不能对内部排列写实现相关断言。
}

TEST(PushHeap, CallerAppendsFirstThenRestoresTheHeapInvariant) {
  std::vector<int> values{9, 7, 8, 1, 2, 3};
  ASSERT_TRUE(std::ranges::is_heap(values));

  values.push_back(10);
  EXPECT_FALSE(std::ranges::is_heap(values));

  auto end = std::ranges::push_heap(values);

  EXPECT_EQ(end, values.end());
  EXPECT_TRUE(std::ranges::is_heap(values));
  EXPECT_EQ(values.front(), 10);

  // push_heap 的前置条件是 `[first,last-1)` 已是 heap，新元素已经位于 last-1；算法只
  // 修复路径，不会替 vector push_back，也不能修复任意损坏的旧 heap。
}

TEST(PopHeap, SelectedRootMovesToTheLastPositionBeforeContainerErase) {
  std::vector<int> values{10, 7, 9, 1, 2, 3, 8};
  ASSERT_TRUE(std::ranges::is_heap(values));

  auto end = std::ranges::pop_heap(values);

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(values.back(), 10);
  EXPECT_TRUE(std::ranges::is_heap(
      std::ranges::subrange(values.begin(), values.end() - 1)));

  values.pop_back();
  EXPECT_TRUE(std::ranges::is_heap(values));
  EXPECT_EQ(values.front(), 9);

  // pop_heap 不缩短容器：把根交换/调整到 last-1，并让前缀继续是 heap；调用者随后从
  // 容器删除尾项。直接再次把整个未缩短范围当原 comparator 的 heap 不满足前置条件。
}

TEST(SortHeap, ItProducesAscendingOrderFromADefaultMaxHeap) {
  std::vector<int> values{4, 1, 7, 3, 8, 5, 2, 6};
  std::ranges::make_heap(values);

  auto end = std::ranges::sort_heap(values);

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(values, (std::vector<int>{1, 2, 3, 4, 5, 6, 7, 8}));
  EXPECT_TRUE(std::ranges::is_sorted(values));
  EXPECT_FALSE(std::ranges::is_heap(values));

  // sort_heap 要求输入已经是 heap；完成后按同一 less 升序排列，原 heap 不变量被消费。
  // 若普通未建堆序列直接调用，违反前置条件。
}

TEST(HeapComparator, GreaterBuildsAMinHeapAndSortsDescending) {
  std::array<int, 6> values{4, 1, 6, 2, 5, 3};

  std::ranges::make_heap(values, std::greater<>{});
  EXPECT_TRUE(std::ranges::is_heap(values, std::greater<>{}));
  EXPECT_EQ(values.front(), 1);

  std::ranges::sort_heap(values, std::greater<>{});
  EXPECT_EQ(values, (std::array<int, 6>{6, 5, 4, 3, 2, 1}));

  // comparator 定义“某元素应排在根之后”的关系；greater 因而让最小值位于根，并在
  // sort_heap 后得到降序。所有操作必须持续使用同一个 comparator。
}

TEST(IsHeapUntil, ItReturnsTheFirstChildThatViolatesTheInvariant) {
  const std::array<int, 7> values{9, 7, 8, 1, 10, 3, 2};

  auto first_bad = std::ranges::is_heap_until(values);

  EXPECT_EQ(first_bad, values.begin() + 4);
  EXPECT_EQ(*first_bad, 10);
  EXPECT_FALSE(std::ranges::is_heap(values));
  EXPECT_TRUE(std::ranges::is_heap(
      std::ranges::subrange(values.begin(), first_bad)));

  // 下标 4 的 10 大于父节点下标 1 的 7，因而是首个违规 child。返回 end 表示完整范围
  // 是 heap；结果指向违规元素而不是其 parent。
}

TEST(RangesHeap, ProjectionBuildsAHeapOfRecordsByPriority) {
  struct Job {
    std::string name;
    int priority;
  };
  std::vector<Job> jobs{{"backup", 2}, {"alert", 9}, {"report", 4}, {"cleanup", 1}};

  std::ranges::make_heap(jobs, std::less<>{}, &Job::priority);

  EXPECT_EQ(jobs.front().name, "alert");
  EXPECT_TRUE(std::ranges::is_heap(jobs, std::less<>{}, &Job::priority));

  jobs.push_back(Job{"incident", 12});
  std::ranges::push_heap(jobs, std::less<>{}, &Job::priority);
  EXPECT_EQ(jobs.front().name, "incident");

  // projection 只决定 heap 顺序，移动的是完整 Job。若 priority 在对象留在 heap 期间被
  // 随意修改，不变量会被破坏，必须重新 make_heap 或执行合适的修复操作。
}

TEST(RangesHeap, PopWithProjectionExposesTheSelectedRecordAtTheTail) {
  struct Job {
    int id;
    int priority;
  };
  std::vector<Job> jobs{{1, 3}, {2, 8}, {3, 5}, {4, 1}};
  std::ranges::make_heap(jobs, std::less<>{}, &Job::priority);

  std::ranges::pop_heap(jobs, std::less<>{}, &Job::priority);

  EXPECT_EQ(jobs.back().id, 2);
  EXPECT_EQ(jobs.back().priority, 8);
  EXPECT_TRUE(std::ranges::is_heap(
      std::ranges::subrange(jobs.begin(), jobs.end() - 1),
      std::less<>{},
      &Job::priority));
}

TEST(HeapBoundaries, EmptyAndSingletonRangesNeedNoReordering) {
  std::vector<int> empty;
  std::array<int, 1> singleton{42};

  EXPECT_TRUE(std::ranges::is_heap(empty));
  EXPECT_TRUE(std::ranges::is_heap(singleton));
  EXPECT_EQ(std::ranges::make_heap(empty), empty.end());
  EXPECT_EQ(std::ranges::sort_heap(singleton), singleton.end());

  // pop_heap 要求非空范围；空范围不能用来调用它。push_heap 可用于单元素范围，因为其
  // 既有 heap 前缀为空且新元素位于末尾。
  EXPECT_EQ(std::ranges::push_heap(singleton), singleton.end());
}

TEST(HeapWorkflow, VectorOperationsAndHeapAlgorithmsFormAPriorityQueue) {
  std::vector<int> pending;

  for (int value : {4, 1, 7, 3}) {
    pending.push_back(value);
    std::push_heap(pending.begin(), pending.end());
  }

  std::vector<int> processed;
  while (!pending.empty()) {
    std::pop_heap(pending.begin(), pending.end());
    processed.push_back(pending.back());
    pending.pop_back();
  }

  EXPECT_EQ(processed, (std::vector<int>{7, 4, 3, 1}));

  // 这正是 priority_queue 的核心工作流；需要受控接口时优先容器适配器，需要访问底层
  // range、批量 make_heap 或自定义处理尾项时才直接组合算法。
}

}  // namespace
