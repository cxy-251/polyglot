// polyglot-covers:
// - cpp.stdlib.algorithms.remove-remove-if-compaction-and-logical-end
// - cpp.stdlib.algorithms.ranges-remove-projection-and-returned-subrange
// - cpp.stdlib.algorithms.remove-copy-and-remove-copy-if-stable-selection
// - cpp.stdlib.algorithms.replace-replace-if-replace-copy-and-replace-copy-if
// - cpp.stdlib.algorithms.unique-adjacent-equivalence-and-logical-end
// - cpp.stdlib.algorithms.unique-copy-stable-run-representatives
// - cpp.stdlib.algorithms.reverse-and-reverse-copy
// - cpp.stdlib.algorithms.rotate-rotate-copy-and-ranges-rotate-return-boundary
// - cpp.stdlib.algorithms.shift-left-right-live-range-and-unspecified-gap
// - cpp.stdlib.algorithms.erase-remove-idiom-versus-container-size

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <iterator>
#include <ranges>
#include <string>
#include <vector>

namespace {

TEST(Remove, ItCompactsKeptValuesAndReturnsALogicalEnd) {
  std::vector<int> values{1, 2, 3, 2, 4, 2};

  auto logical_end = std::remove(values.begin(), values.end(), 2);

  EXPECT_EQ(std::vector<int>(values.begin(), logical_end),
            (std::vector<int>{1, 3, 4}));
  EXPECT_EQ(values.size(), 6U);

  // remove 不知道容器所有权，只把保留元素稳定地移动到前部并返回逻辑尾。逻辑尾之后的
  // 元素仍是有效对象，但值未指定，不能把某个实现留下的旧值当成标准语义。
  values.erase(logical_end, values.end());
  EXPECT_EQ(values, (std::vector<int>{1, 3, 4}));
}

TEST(RemoveIf, EraseRemoveSeparatesElementMovementFromStorageErasure) {
  std::vector<int> values{1, 2, 3, 4, 5, 6};

  auto logical_end = std::remove_if(values.begin(), values.end(), [](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(std::distance(values.begin(), logical_end), 3);
  EXPECT_EQ(std::vector<int>(values.begin(), logical_end),
            (std::vector<int>{1, 3, 5}));

  values.erase(logical_end, values.end());
  EXPECT_EQ(values.size(), 3U);

  // C++20 的 std::erase_if(values, pred) 封装了同一容器级工作流；算法本身仍必须可用于
  // 数组、裸 iterator 区间和没有 erase 成员的范围，所以不会擅自改变 size。
}

TEST(RangesRemove, ProjectionSelectsTheComparedRecordMember) {
  struct Item {
    int id;
    std::string label;
  };
  std::vector<Item> items{{1, "keep"}, {2, "drop"}, {3, "keep"}, {2, "drop"}};

  auto removed_tail = std::ranges::remove(items, 2, &Item::id);

  EXPECT_EQ(removed_tail.begin(), items.begin() + 2);
  EXPECT_EQ(removed_tail.end(), items.end());
  EXPECT_EQ(items[0].id, 1);
  EXPECT_EQ(items[1].id, 3);

  // ranges::remove 返回 `[logical_end, original_end)` 的 subrange，而不是只返回一个
  // iterator；projection 只参与比较，移动的仍是完整 Item。
  items.erase(removed_tail.begin(), removed_tail.end());
  ASSERT_EQ(items.size(), 2U);
  EXPECT_EQ(items[1].label, "keep");
}

TEST(RemoveCopyIf, ItCopiesKeptElementsStablyAndLeavesTheSourceUntouched) {
  const std::array<int, 6> source{4, 1, 6, 3, 8, 5};
  std::vector<int> odd;

  auto output_end = std::remove_copy_if(
      source.begin(),
      source.end(),
      std::back_inserter(odd),
      [](int value) {
        return value % 2 == 0;
      });
  *output_end = 9;

  EXPECT_EQ(odd, (std::vector<int>{1, 3, 5, 9}));
  EXPECT_EQ(source, (std::array<int, 6>{4, 1, 6, 3, 8, 5}));

  // remove_copy_if 的谓词为 true 表示“不复制”；结果保持保留项的相对顺序。普通输出
  // iterator 仍要求调用者准备容量，back_inserter 才会增长容器。
}

TEST(RemoveCopy, EqualityFormCopiesEveryElementExceptTheRequestedValue) {
  const std::array<int, 6> source{1, 2, 1, 3, 1, 4};
  std::array<int, 3> output{};

  auto result = std::ranges::remove_copy(source, output.begin(), 1);

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, output.end());
  EXPECT_EQ(output, (std::array<int, 3>{2, 3, 4}));

  // remove_copy 是按相等值排除的稳定复制；目标必须容纳所有未被删除的项。算法不会先
  // 统计数量，也不会因为固定数组已满而自动停止。
}

TEST(Replace, InPlaceFormsAssignOnlyMatchingElements) {
  std::vector<int> values{1, 2, 3, 2, 4};

  std::ranges::replace(values, 2, 20);
  std::ranges::replace_if(values, [](int value) {
    return value % 2 == 1;
  }, -1);

  EXPECT_EQ(values, (std::vector<int>{-1, 20, -1, 20, 4}));

  // replace 不重排、不缩短 range，只对命中位置做赋值；若赋值可能抛异常，已经处理过的
  // 前缀不会自动回滚，因此不能假设强异常保证。
}

TEST(ReplaceCopy, ItBuildsAChangedOutputWithoutMutatingTheInput) {
  const std::array<int, 5> source{1, 2, 1, 3, 1};
  std::array<int, 5> destination{};

  auto result = std::ranges::replace_copy(source, destination.begin(), 1, 9);

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, destination.end());
  EXPECT_EQ(destination, (std::array<int, 5>{9, 2, 9, 3, 9}));
  EXPECT_EQ(source, (std::array<int, 5>{1, 2, 1, 3, 1}));
}

TEST(ReplaceCopyIf, PredicateSelectsWhichCopiedValuesAreSubstituted) {
  const std::array<int, 5> source{1, 2, 3, 4, 5};
  std::array<int, 5> output{};

  auto result = std::ranges::replace_copy_if(
      source,
      output.begin(),
      [](int value) {
        return value % 2 == 0;
      },
      0);

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, output.end());
  EXPECT_EQ(output, (std::array<int, 5>{1, 0, 3, 0, 5}));
  EXPECT_EQ(source, (std::array<int, 5>{1, 2, 3, 4, 5}));
}

TEST(Unique, ItCollapsesAdjacentEquivalentRunsOnly) {
  std::vector<int> values{1, 1, 2, 1, 1, 3, 3};

  auto logical_end = std::unique(values.begin(), values.end());

  EXPECT_EQ(std::vector<int>(values.begin(), logical_end),
            (std::vector<int>{1, 2, 1, 3}));
  EXPECT_EQ(values.size(), 7U);

  // unique 只比较相邻项，不能直接做“全局去重”；要合并所有相等值通常先 sort，再
  // unique，再 erase。与 remove 一样，逻辑尾之后的值未指定。
  values.erase(logical_end, values.end());
  EXPECT_EQ(values, (std::vector<int>{1, 2, 1, 3}));
}

TEST(Unique, CustomEquivalenceDefinesRunsRatherThanCanonicalValues) {
  std::vector<int> values{11, 12, 19, 21, 22, 35};

  auto tail = std::ranges::unique(values, [](int left, int right) {
    return left / 10 == right / 10;
  });
  values.erase(tail.begin(), tail.end());

  EXPECT_EQ(values, (std::vector<int>{11, 21, 35}));

  // 每个相邻等价 run 保留第一项。谓词应表达等价关系；若不对称或不传递，算法调用不
  // 满足其语义要求，不能把偶然结果当成可靠的分组规则。
}

TEST(UniqueCopy, ItWritesOneStableRepresentativeFromEachAdjacentRun) {
  const std::array<int, 8> source{1, 1, 1, 2, 3, 3, 2, 2};
  std::vector<int> representatives;

  auto result = std::ranges::unique_copy(source, std::back_inserter(representatives));

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(representatives, (std::vector<int>{1, 2, 3, 2}));

  // unique_copy 不改源范围，适合同时保留原数据；输出与输入不能采用不满足标准要求的
  // 重叠布局。末尾再次出现的 2 属于新 run，因此仍会输出。
}

TEST(Reverse, InPlaceAndCopyingFormsHaveDifferentOwnershipEffects) {
  std::vector<int> values{1, 2, 3, 4};
  std::vector<int> copied;

  auto copy_end = std::reverse_copy(
      values.begin(), values.end(), std::back_inserter(copied));
  std::ranges::reverse(values);
  *copy_end = 0;

  EXPECT_EQ(values, (std::vector<int>{4, 3, 2, 1}));
  EXPECT_EQ(copied, (std::vector<int>{4, 3, 2, 1, 0}));

  // reverse 通过 iter_swap 原地交换首尾，需要双向且可交换的 iterator；reverse_copy
  // 保留源范围，但输出不能与输入采用会覆盖未读元素的重叠布局。
}

TEST(Rotate, LeftRotationReturnsTheNewPositionOfTheOldFirstElement) {
  std::array<int, 5> values{1, 2, 3, 4, 5};

  auto old_first = std::rotate(values.begin(), values.begin() + 2, values.end());

  EXPECT_EQ(values, (std::array<int, 5>{3, 4, 5, 1, 2}));
  EXPECT_EQ(old_first, values.begin() + 3);

  // `[first,middle)` 被移到末尾且两段内部顺序保持；返回位置指向旋转后的旧 first，
  // 也就是新序列中后半段的开头。
}

TEST(RangesRotate, ReturnedSubrangeDescribesTheMovedPrefixAtTheNewTail) {
  std::vector<int> values{1, 2, 3, 4, 5, 6};

  auto moved_prefix = std::ranges::rotate(values, values.begin() + 4);

  EXPECT_EQ(values, (std::vector<int>{5, 6, 1, 2, 3, 4}));
  EXPECT_EQ(moved_prefix.begin(), values.begin() + 2);
  EXPECT_EQ(moved_prefix.end(), values.end());
  EXPECT_EQ(std::vector<int>(moved_prefix.begin(), moved_prefix.end()),
            (std::vector<int>{1, 2, 3, 4}));

  // ranges 版本用 subrange 返回 `[旧 first 的新位置, last)`，直接标出被搬到尾部的
  // 原前缀。若 middle==first，返回空尾区间；若 middle==last，返回整个原区间。
}

TEST(RotateCopy, ItWritesTheRotatedOrderWithoutChangingTheSource) {
  const std::array<int, 5> source{1, 2, 3, 4, 5};
  std::array<int, 5> output{};

  auto result = std::ranges::rotate_copy(
      source, source.begin() + 2, output.begin());

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, output.end());
  EXPECT_EQ(output, (std::array<int, 5>{3, 4, 5, 1, 2}));
  EXPECT_EQ(source, (std::array<int, 5>{1, 2, 3, 4, 5}));

  // rotate_copy 保留源并复制两段交换后的顺序；输出不能覆盖尚未读取的源元素。与原地
  // rotate 不同，它返回输入/输出终点，而不是旧 first 的新位置。
}

TEST(ShiftLeft, OnlyTheReturnedPrefixHasSpecifiedPostcondition) {
  std::array<int, 6> values{1, 2, 3, 4, 5, 6};

  auto live_end = std::shift_left(values.begin(), values.end(), 2);

  EXPECT_EQ(live_end, values.begin() + 4);
  EXPECT_EQ(std::vector<int>(values.begin(), live_end),
            (std::vector<int>{3, 4, 5, 6}));

  // 左移后的 `[first,live_end)` 有规定值；尾部两个对象仍存活，但值未指定。shift_left
  // 不 erase、不 resize，n 大于等于长度时返回 first，整个范围都不属于结果区间。
}

TEST(ShiftRight, OnlyTheReturnedSuffixHasSpecifiedPostcondition) {
  std::array<int, 6> values{1, 2, 3, 4, 5, 6};

  auto live_begin = std::shift_right(values.begin(), values.end(), 2);

  EXPECT_EQ(live_begin, values.begin() + 2);
  EXPECT_EQ(std::vector<int>(live_begin, values.end()),
            (std::vector<int>{1, 2, 3, 4}));

  // 右移后的 `[live_begin,last)` 有规定值；前部空洞值未指定。算法会选择不会覆盖未读
  // 元素的移动方向，但不会创建默认值或扩展容器。
}

TEST(Shift, ZeroAndOversizedCountsHaveExplicitBoundaries) {
  std::array<int, 3> unchanged{1, 2, 3};
  std::array<int, 3> exhausted{1, 2, 3};

  EXPECT_EQ(std::shift_left(unchanged.begin(), unchanged.end(), 0), unchanged.end());
  EXPECT_EQ(unchanged, (std::array<int, 3>{1, 2, 3}));
  EXPECT_EQ(std::shift_right(exhausted.begin(), exhausted.end(), 9), exhausted.end());

  // shift_right 的 n>=length 返回 last，表示规定结果后缀为空；此时标准不要求移动元素。
  // n 必须非负，把负数当作反向移动并不是接口约定。
}

}  // namespace
