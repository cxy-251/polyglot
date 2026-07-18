// polyglot-covers:
// - cpp.stdlib.algorithms.sort-and-ranges-sort-return
// - cpp.stdlib.algorithms.sort-strict-weak-order-precondition
// - cpp.stdlib.algorithms.ranges-sort-projection
// - cpp.stdlib.algorithms.stable-sort-equivalent-element-order
// - cpp.stdlib.algorithms.partial-sort-sorted-prefix-and-partition
// - cpp.stdlib.algorithms.partial-sort-copy-bounded-output
// - cpp.stdlib.algorithms.nth-element-selection-partition-guarantee
// - cpp.stdlib.algorithms.is-sorted-and-is-sorted-until
// - cpp.stdlib.algorithms.sort-iterator-position-versus-element-identity
// - cpp.stdlib.algorithms.constexpr-sort-cpp20

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <ranges>
#include <string>
#include <vector>

namespace {

TEST(Sort, ItProducesAnAscendingPermutationAndRangesReturnsTheEnd) {
  std::vector<int> values{5, 1, 4, 1, 3, 2};

  auto end = std::ranges::sort(values);

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(values, (std::vector<int>{1, 1, 2, 3, 4, 5}));

  // sort 只重排元素，保持原多重集合；ranges 版本返回最终 iterator，临时非 borrowed
  // range 则返回 dangling。等价元素之间没有稳定性承诺。
}

TEST(Sort, DescendingOrderUsesTheSameComparatorForEveryOrderingDecision) {
  std::array<int, 5> values{3, 1, 5, 2, 4};

  std::ranges::sort(values, std::greater<>{});

  EXPECT_EQ(values, (std::array<int, 5>{5, 4, 3, 2, 1}));
  EXPECT_TRUE(std::ranges::is_sorted(values, std::greater<>{}));

  // comparator 必须表达 strict weak ordering；`<=`、会随调用改变规则的有状态比较器，
  // 或对同一对象 comp(x,x)==true 都违反算法前置条件，不能用来表达“也包含相等”。
}

TEST(RangesSort, ProjectionOrdersRecordsByASelectedKey) {
  struct User {
    std::string name;
    int age;
  };
  std::vector<User> users{{"Ada", 37}, {"Linus", 31}, {"Bjarne", 35}};

  std::ranges::sort(users, std::less<>{}, &User::age);

  EXPECT_EQ(users[0].name, "Linus");
  EXPECT_EQ(users[1].name, "Bjarne");
  EXPECT_EQ(users[2].name, "Ada");

  // projection 先取得 age，比较器只比较投影结果；被交换、移动的仍是完整 User。
}

TEST(StableSort, EquivalentKeysKeepTheirOriginalRelativeOrder) {
  struct Event {
    int priority;
    int sequence;
  };
  std::vector<Event> events{{2, 1}, {1, 2}, {2, 3}, {1, 4}, {2, 5}};

  std::ranges::stable_sort(events, std::less<>{}, &Event::priority);

  EXPECT_EQ(events[0].sequence, 2);
  EXPECT_EQ(events[1].sequence, 4);
  EXPECT_EQ(events[2].sequence, 1);
  EXPECT_EQ(events[3].sequence, 3);
  EXPECT_EQ(events[4].sequence, 5);

  // stable_sort 对比较意义下等价的元素保持输入顺序；普通 sort 没有这个保证。稳定排序
  // 常用于先按次关键字排序，再按主关键字稳定排序。
}

TEST(StableSortWorkflow, LaterStableSortCanAddAHigherPriorityKey) {
  struct Row {
    int group;
    int score;
    int id;
  };
  std::vector<Row> rows{{2, 80, 1}, {1, 70, 2}, {2, 60, 3}, {1, 90, 4}};

  std::ranges::stable_sort(rows, std::less<>{}, &Row::score);
  std::ranges::stable_sort(rows, std::less<>{}, &Row::group);

  EXPECT_EQ(rows[0].id, 2);
  EXPECT_EQ(rows[1].id, 4);
  EXPECT_EQ(rows[2].id, 3);
  EXPECT_EQ(rows[3].id, 1);

  // 第二次稳定排序把 group 设为主关键字，同时保留每个 group 中第一次得到的 score
  // 顺序。若第二次使用不稳定 sort，这个两关键字工作流就没有保证。
}

TEST(PartialSort, ItSortsOnlyTheRequestedSmallestPrefix) {
  std::vector<int> values{9, 1, 8, 2, 7, 3, 6, 4, 5};
  auto middle = values.begin() + 4;

  std::partial_sort(values.begin(), middle, values.end());

  EXPECT_EQ(std::vector<int>(values.begin(), middle),
            (std::vector<int>{1, 2, 3, 4}));
  EXPECT_TRUE(std::is_sorted(values.begin(), middle));
  EXPECT_TRUE(std::all_of(middle, values.end(), [middle](int value) {
    return value >= *(middle - 1);
  }));

  // `[first,middle)` 是全范围最小的 K 项并已排序；尾部只保证不小于前缀中的项，不保证
  // 自身有序。只要前 K 名时不必为完整 sort 付费。
}

TEST(PartialSort, EmptyPrefixIsAWellDefinedNoOp) {
  std::array<int, 4> values{4, 1, 3, 2};
  const auto original = values;

  std::ranges::partial_sort(values, values.begin());

  EXPECT_EQ(values, original);

  // middle==first 请求零个结果；middle 必须属于 `[first,last]`，越界 iterator 不是可
  // 用来测试的边界情况。
}

TEST(PartialSortCopy, OutputCapacityDeterminesHowManySmallestItemsAreWritten) {
  const std::array<int, 7> source{7, 2, 5, 1, 6, 3, 4};
  std::array<int, 3> smallest{};

  auto result = std::ranges::partial_sort_copy(source, smallest);

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, smallest.end());
  EXPECT_EQ(smallest, (std::array<int, 3>{1, 2, 3}));
  EXPECT_EQ(source, (std::array<int, 7>{7, 2, 5, 1, 6, 3, 4}));

  // 输出长度是 min(input_size, output_size)，结果已排序且源不变。与 copy 算法不同，
  // 这里输出 range 的边界同时表达“最多保留多少项”。
}

TEST(PartialSortCopy, LargerOutputWritesOnlyTheAvailableInputCount) {
  const std::array<int, 3> source{3, 1, 2};
  std::array<int, 5> output{-1, -1, -1, -1, -1};

  auto result = std::ranges::partial_sort_copy(source, output);

  EXPECT_EQ(result.out, output.begin() + 3);
  EXPECT_EQ(output, (std::array<int, 5>{1, 2, 3, -1, -1}));

  // input 较短时，只写入实际输入数量；必须使用 result.out 判断已填充尾部。
}

TEST(NthElement, NthPositionMatchesFullSortWithoutSortingEitherSide) {
  std::vector<int> values{9, 1, 8, 2, 7, 3, 6, 4, 5};
  auto nth = values.begin() + 4;

  std::nth_element(values.begin(), nth, values.end());

  EXPECT_EQ(*nth, 5);
  EXPECT_TRUE(std::all_of(values.begin(), nth, [nth](int value) {
    return value <= *nth;
  }));
  EXPECT_TRUE(std::all_of(nth + 1, values.end(), [nth](int value) {
    return value >= *nth;
  }));

  // nth_element 只保证 *nth 等于完整排序后该位置的值，并让左侧没有大于右侧的元素；
  // 两侧内部顺序未指定。求中位数或 top-K 边界时通常比完整排序合适。
}

TEST(NthElement, RangesProjectionSelectsARecordOrderStatistic) {
  struct Sample {
    std::string name;
    int latency;
  };
  std::vector<Sample> samples{
      {"a", 40}, {"b", 10}, {"c", 50}, {"d", 20}, {"e", 30}};
  auto median = samples.begin() + 2;

  auto end = std::ranges::nth_element(
      samples, median, std::less<>{}, &Sample::latency);

  EXPECT_EQ(end, samples.end());
  EXPECT_EQ(median->latency, 30);

  // ranges::nth_element 返回 last；nth iterator 仍由调用者提供，projection 只决定顺序。
}

TEST(IsSortedUntil, ItReturnsTheSecondElementOfTheFirstInversion) {
  const std::array<int, 6> values{1, 2, 4, 3, 5, 6};

  auto first_bad = std::ranges::is_sorted_until(values);

  EXPECT_EQ(first_bad, values.begin() + 3);
  EXPECT_EQ(*first_bad, 3);
  EXPECT_FALSE(std::ranges::is_sorted(values));
  EXPECT_TRUE(std::ranges::is_sorted(
      std::ranges::subrange(values.begin(), first_bad)));

  // 返回位置是破坏有序关系的后一项，不是前一项 4；完全有序或空范围返回 end。
}

TEST(SortIteratorSemantics, IteratorsKeepPositionsNotOriginalElementIdentity) {
  std::vector<int> values{30, 10, 20};
  auto first_position = values.begin();

  std::ranges::sort(values);

  EXPECT_EQ(first_position, values.begin());
  EXPECT_EQ(*first_position, 10);

  // sort 没有改变 vector 存储或使位置 iterator 失效，但该位置现在装着别的值。不能用
  // 排序前保存的 iterator 继续代表“原来的那个逻辑实体”；需要稳定身份时保存 ID。
}

constexpr bool ConstexprSortWorks() {
  std::array<int, 5> values{5, 1, 4, 2, 3};
  std::sort(values.begin(), values.end());
  return values == std::array<int, 5>{1, 2, 3, 4, 5};
}

static_assert(ConstexprSortWorks());

TEST(ConstexprSort, Cpp20PermitsSortingDuringConstantEvaluation) {
  EXPECT_TRUE(ConstexprSortWorks());

  // C++20 将许多非并行算法 constexpr 化；是否能常量求值仍取决于元素操作和分配等
  // 全部步骤能否出现在常量表达式中，并不意味着任意运行期 comparator 都可用。
}

}  // namespace
