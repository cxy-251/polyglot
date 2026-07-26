// polyglot-covers:
// - cpp.stdlib.algorithms.copy-copy-n-and-ranges-copy-result
// - cpp.stdlib.algorithms.copy-if-stable-selection
// - cpp.stdlib.algorithms.copy-backward-overlap-direction
// - cpp.stdlib.algorithms.move-and-move-backward-ownership-transfer
// - cpp.stdlib.algorithms.fill-and-fill-n
// - cpp.stdlib.algorithms.unary-transform-in-place-and-projection-workflow
// - cpp.stdlib.algorithms.binary-transform-shortest-explicit-range
// - cpp.stdlib.algorithms.generate-and-generate-n-state
// - cpp.stdlib.algorithms.swap-ranges-and-ranges-swap-ranges-result
// - cpp.stdlib.algorithms.output-range-capacity-precondition

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <iterator>
#include <memory>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(Copy, RangesResultReportsHowMuchInputAndOutputWereConsumed) {
  const std::array<int, 4> source{2, 3, 5, 7};
  std::array<int, 6> destination{};

  auto result = std::ranges::copy(source, destination.begin() + 1);

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, destination.begin() + 5);
  EXPECT_EQ(destination, (std::array<int, 6>{0, 2, 3, 5, 7, 0}));

  // ranges::copy 返回 in_out_result，便于继续处理输入尾部或输出尾部。算法不检查目标
  // 容量，调用者必须保证从 out 起有足够可写位置，或使用 back_inserter 等增长适配器。
}

TEST(CopyN, CountControlsTheSourcePrefixAndTheReturnedOutputEnd) {
  const std::array<int, 5> source{1, 2, 3, 4, 5};
  std::vector<int> destination;

  auto output_end = std::copy_n(source.begin() + 1, 3, std::back_inserter(destination));
  *output_end = 9;

  EXPECT_EQ(destination, (std::vector<int>{2, 3, 4, 9}));

  // copy_n 没有输入 sentinel，必须保证 first 后至少有 count 个可读元素；返回输出位置。
  // back_insert_iterator 的返回位置仍可继续赋值并 push_back。
}

TEST(CopyIf, SelectedElementsKeepTheirOriginalRelativeOrder) {
  const std::vector<int> source{5, 2, 4, 1, 3, 6};
  std::vector<int> evens;

  std::ranges::copy_if(source, std::back_inserter(evens), [](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(evens, (std::vector<int>{2, 4, 6}));

  // copy_if 是稳定选择：被保留元素的相对顺序不变。输出不能落入会被同次读取覆盖的
  // 输入区间；原地删除应使用 remove_if/erase_if，而不是重叠 copy_if。
}

TEST(CopyBackward, RightShiftNeedsBackwardTraversalToProtectUnreadElements) {
  std::array<int, 6> values{1, 2, 3, 4, 0, 0};

  auto new_begin = std::copy_backward(values.begin(), values.begin() + 4, values.end());

  EXPECT_EQ(new_begin, values.begin() + 2);
  EXPECT_EQ(values, (std::array<int, 6>{1, 2, 1, 2, 3, 4}));

  // 目标向右与源重叠时，从末尾 copy_backward 才不会先覆盖尚未读取的值；目标向左时
  // 用 copy。选错方向会违反重叠前置条件，不是“结果偶尔不同”的可移植操作。
}

TEST(Move, ItTransfersMoveOnlyElementsAndLeavesSourceObjectsValid) {
  std::vector<std::unique_ptr<int>> source;
  source.push_back(std::make_unique<int>(7));
  source.push_back(std::make_unique<int>(11));
  std::vector<std::unique_ptr<int>> destination(2);

  auto result = std::ranges::move(source, destination.begin());

  EXPECT_EQ(result.in, source.end());
  EXPECT_EQ(result.out, destination.end());
  EXPECT_EQ(source[0], nullptr);
  EXPECT_EQ(source[1], nullptr);
  EXPECT_EQ(*destination[0], 7);
  EXPECT_EQ(*destination[1], 11);

  // move 算法对每项执行 `*out = ranges::iter_move(in)`；源容器仍保留同样 size，
  // 元素处于各自类型规定的 moved-from 状态。它不会自动 erase 源 range。
}

TEST(MoveBackward, RightShiftOfMoveOnlyElementsUsesTheSafeOverlapDirection) {
  std::array<std::unique_ptr<int>, 4> owners{
      std::make_unique<int>(1),
      std::make_unique<int>(2),
      nullptr,
      nullptr,
  };

  auto begin = std::move_backward(owners.begin(), owners.begin() + 2, owners.end());

  EXPECT_EQ(begin, owners.begin() + 2);
  EXPECT_EQ(owners[0], nullptr);
  EXPECT_EQ(owners[1], nullptr);
  EXPECT_EQ(*owners[2], 1);
  EXPECT_EQ(*owners[3], 2);

  // move_backward 与 copy_backward 的方向规则相同，只是赋值使用移动语义；适合把
  // move-only 区间向右挪。目标尾边界必须提供足够空间。
}

TEST(Fill, WholeRangeAndCountedPrefixAssignTheSameValueRepeatedly) {
  std::array<std::string, 5> values;

  std::ranges::fill(values, "unset");
  auto end = std::fill_n(values.begin() + 1, 3, std::string{"ready"});

  EXPECT_EQ(end, values.begin() + 4);
  EXPECT_EQ(values,
            (std::array<std::string, 5>{
                "unset", "ready", "ready", "ready", "unset"}));

  // fill 覆盖完整输出 range，fill_n 从 first 写 count 次并返回尾位置。赋入每个元素的是
  // 同一个 value 的赋值结果，不是每次调用 factory；需要逐项新值时使用 generate。
}

TEST(Transform, UnaryFormCanSafelyWriteBackToTheSamePositions) {
  std::vector<int> values{1, 2, 3, 4};

  auto output_end = std::transform(
      values.begin(),
      values.end(),
      values.begin(),
      [](int value) {
        return value * value;
      });

  EXPECT_EQ(output_end, values.end());
  EXPECT_EQ(values, (std::vector<int>{1, 4, 9, 16}));

  // unary transform 明确允许 output==first1 的逐元素原地变换；其他导致当前输出覆盖
  // 尚未读取输入的重叠方式不安全。返回值是最终输出位置。
}

TEST(Transform, RangesProjectionCanFeedARecordMemberToTheCallable) {
  struct Record {
    int score;
  };
  const std::vector<Record> records{{2}, {3}, {5}};
  std::vector<int> doubled;

  auto result = std::ranges::transform(
      records,
      std::back_inserter(doubled),
      [](int score) {
        return score * 2;
      },
      &Record::score);

  EXPECT_EQ(result.in, records.end());
  EXPECT_EQ(doubled, (std::vector<int>{4, 6, 10}));

  // ranges::transform 先投影 Record::score，再调用 unary operation；结果对象同时返回
  // 输入和输出终点。projection 与 transform callable 各自只负责一层语义。
}

TEST(Transform, BinaryClassicFormUsesTheFirstRangeLengthAsItsContract) {
  const std::vector<int> left{1, 2, 3};
  const std::vector<int> right{10, 20, 30, 40};
  std::vector<int> sums(3);

  std::transform(
      left.begin(),
      left.end(),
      right.begin(),
      sums.begin(),
      std::plus<>{});

  EXPECT_EQ(sums, (std::vector<int>{11, 22, 33}));

  // 经典 binary transform 只接第二路 begin，默认它至少与第一路一样长；多余 right
  // 元素不处理，过短则越界。ranges overload 接受两路 sentinel，会在任一路结束时停止。
}

TEST(Transform, RangesBinaryFormStopsWhenEitherInputRangeEnds) {
  const std::array<int, 4> left{1, 2, 3, 4};
  const std::array<int, 2> right{10, 20};
  std::array<int, 4> output{-1, -1, -1, -1};

  auto result = std::ranges::transform(
      left, right, output.begin(), std::plus<>{});

  EXPECT_EQ(result.in1, left.begin() + 2);
  EXPECT_EQ(result.in2, right.end());
  EXPECT_EQ(result.out, output.begin() + 2);
  EXPECT_EQ(output, (std::array<int, 4>{11, 22, -1, -1}));

  // ranges 二元版本同时接收两路边界，在较短输入结束时停止；结果对象明确指出每路消费
  // 位置。它不会用默认值补齐较长输入，也不会写剩余输出槽。
}

TEST(Generate, GeneratorStateProducesANewValueForEachOutputElement) {
  std::array<int, 5> values{};
  int next = 1;

  std::ranges::generate(values, [&next] {
    const int current = next;
    next *= 2;
    return current;
  });

  EXPECT_EQ(values, (std::array<int, 5>{1, 2, 4, 8, 16}));
  EXPECT_EQ(next, 32);

  // generate 每个元素调用一次 nullary generator，适合序列状态；调用顺序对普通顺序
  // overload 是遍历顺序。generator 不得通过其他途径使输出 iterator 失效。
}

TEST(GenerateN, ItWritesOnlyTheRequestedPrefixAndReturnsTheOutputEnd) {
  std::vector<int> values(5, -1);
  int next = 10;

  auto end = std::generate_n(values.begin() + 1, 3, [&next] {
    return next++;
  });

  EXPECT_EQ(end, values.begin() + 4);
  EXPECT_EQ(values, (std::vector<int>{-1, 10, 11, 12, -1}));

  // generate_n 不知道容器 end，count 必须落在有效输出范围；它不会 resize 容器。
}

TEST(SwapRanges, RangesResultReportsBothFinalPositions) {
  std::array<int, 3> first{1, 2, 3};
  std::array<int, 4> second{4, 5, 6, 7};

  auto result = std::ranges::swap_ranges(first, second);

  EXPECT_EQ(first, (std::array<int, 3>{4, 5, 6}));
  EXPECT_EQ(second, (std::array<int, 4>{1, 2, 3, 7}));
  EXPECT_EQ(result.in1, first.end());
  EXPECT_EQ(result.in2, second.begin() + 3);

  // ranges::swap_ranges 在较短 range 结束时停止并返回两路位置；通过 iter_swap 支持代理
  // iterator。两个输入区间不能以会让同一元素参与不受支持方式的重叠布局传入。
}

}  // namespace
