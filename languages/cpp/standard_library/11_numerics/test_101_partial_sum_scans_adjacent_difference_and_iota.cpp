// polyglot-covers:
// - cpp.stdlib.numeric.partial-sum-ordered-prefix-fold
// - cpp.stdlib.numeric.partial-sum-in-place-and-output-end
// - cpp.stdlib.numeric.exclusive-scan-excludes-current-element
// - cpp.stdlib.numeric.inclusive-scan-includes-current-element-and-init
// - cpp.stdlib.numeric.scan-generalized-noncommutative-sum-grouping
// - cpp.stdlib.numeric.transform-exclusive-scan-and-untransformed-init
// - cpp.stdlib.numeric.transform-inclusive-scan-with-and-without-init
// - cpp.stdlib.numeric.adjacent-difference-first-element-and-pairs
// - cpp.stdlib.numeric.adjacent-difference-in-place-inverse-workflow
// - cpp.stdlib.numeric.iota-incremented-value-copy-and-boundaries
// - cpp.stdlib.numeric.parallel-scan-nonoverlap-and-pure-operation

#include <gtest/gtest.h>

#include <array>
#include <execution>
#include <functional>
#include <numeric>
#include <string>
#include <vector>

namespace {

TEST(PartialSum, ItWritesEveryOrderedPrefixFoldAndReturnsOutputEnd) {
  const std::array<int, 5> values{1, 2, 3, 4, 5};
  std::array<int, 5> prefixes{};

  auto end = std::partial_sum(values.begin(), values.end(), prefixes.begin());

  EXPECT_EQ(end, prefixes.end());
  EXPECT_EQ(prefixes, (std::array<int, 5>{1, 3, 6, 10, 15}));

  // 第 K 个输出包含输入 0..K；首项直接复制，之后严格按输入顺序用 accumulator 折叠。
  // 输出必须至少与输入一样长，算法不会检查固定缓冲区容量。
}

TEST(PartialSum, CustomOperationAndInPlaceOutputAreSupported) {
  std::array<int, 4> values{2, 3, 4, 5};

  auto end = std::partial_sum(
      values.begin(), values.end(), values.begin(), std::multiplies<>{});

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(values, (std::array<int, 4>{2, 6, 24, 120}));

  // 非 policy overload 明确允许 result==first，因为每个旧输入会在覆盖前保存。其他
  // 任意偏移重叠没有同样保证。
}

TEST(PartialSum, EmptyInputReturnsTheOriginalOutputPosition) {
  const std::vector<int> empty;
  std::array<int, 2> output{7, 8};

  auto end = std::partial_sum(empty.begin(), empty.end(), output.begin());

  EXPECT_EQ(end, output.begin());
  EXPECT_EQ(output, (std::array<int, 2>{7, 8}));
}

TEST(Scans, ExclusiveAndInclusiveDifferAtTheCurrentInputElement) {
  const std::array<int, 4> values{1, 2, 3, 4};
  std::array<int, 4> exclusive{};
  std::array<int, 4> inclusive{};

  auto exclusive_end = std::exclusive_scan(
      values.begin(), values.end(), exclusive.begin(), 10);
  auto inclusive_end = std::inclusive_scan(
      values.begin(), values.end(), inclusive.begin());

  EXPECT_EQ(exclusive_end, exclusive.end());
  EXPECT_EQ(inclusive_end, inclusive.end());
  EXPECT_EQ(exclusive, (std::array<int, 4>{10, 11, 13, 16}));
  EXPECT_EQ(inclusive, (std::array<int, 4>{1, 3, 6, 10}));

  // exclusive 的位置 K 只含 init 和 K 之前的输入；inclusive 的位置 K 包含当前输入。
}

TEST(InclusiveScan, ExplicitInitParticipatesBeforeTheFirstInput) {
  const std::array<int, 3> values{2, 3, 4};
  std::array<int, 3> output{};

  std::inclusive_scan(
      values.begin(),
      values.end(),
      output.begin(),
      std::multiplies<>{},
      10);

  EXPECT_EQ(output, (std::array<int, 3>{20, 60, 240}));

  // 带 init 的 inclusive_scan 首项是 op(init,input[0])；不带 init 时首项直接来自
  // input[0]。参数顺序是 output、binary_op、init，和 exclusive_scan 不同。
}

TEST(Scans, InPlaceOperationIsAllowedForNonPolicyOverloads) {
  std::array<int, 4> exclusive{1, 2, 3, 4};
  std::array<int, 4> inclusive{1, 2, 3, 4};

  std::exclusive_scan(
      exclusive.begin(), exclusive.end(), exclusive.begin(), 0);
  std::inclusive_scan(
      inclusive.begin(), inclusive.end(), inclusive.begin());

  EXPECT_EQ(exclusive, (std::array<int, 4>{0, 1, 3, 6}));
  EXPECT_EQ(inclusive, (std::array<int, 4>{1, 3, 6, 10}));

  // 非 policy scan 允许 result==first；带 execution policy 时 iterator 要求更强，重叠
  // 约束应按具体 overload 条文处理，最稳妥是使用独立输出范围。
}

TEST(Scans, UseAssociativeOperationsBecausePrefixGroupingMayVary) {
  const std::array<unsigned, 4> flags{0x01U, 0x02U, 0x04U, 0x08U};
  std::array<unsigned, 4> prefixes{};

  std::inclusive_scan(
      flags.begin(), flags.end(), prefixes.begin(), std::bit_or<>{});

  EXPECT_EQ(prefixes, (std::array<unsigned, 4>{0x01U, 0x03U, 0x07U, 0x0FU}));

  // scan 保持每个前缀的元素次序，但 generalized noncommutative sum 可以改变括号分组。
  // 对不满足数学结合律的操作（尤其浮点加法），结果可能随实现或并行分组变化。
}

TEST(TransformExclusiveScan, InitIsNotPassedThroughTheUnaryTransform) {
  const std::array<int, 4> values{1, 2, 3, 4};
  std::array<int, 4> output{};

  auto end = std::transform_exclusive_scan(
      values.begin(),
      values.end(),
      output.begin(),
      10,
      std::plus<>{},
      [](int value) {
        return value * value;
      });

  EXPECT_EQ(end, output.end());
  EXPECT_EQ(output, (std::array<int, 4>{10, 11, 15, 24}));

  // 输出依次为 10、10+1、10+1+4、10+1+4+9；init 10 不会先平方。
}

TEST(TransformInclusiveScan, ItSupportsFormsWithAndWithoutInit) {
  const std::array<int, 3> values{1, 2, 3};
  std::array<int, 3> without_init{};
  std::array<int, 3> with_init{};
  auto square = [](int value) {
    return value * value;
  };

  std::transform_inclusive_scan(
      values.begin(),
      values.end(),
      without_init.begin(),
      std::plus<>{},
      square);
  std::transform_inclusive_scan(
      values.begin(),
      values.end(),
      with_init.begin(),
      std::plus<>{},
      square,
      10);

  EXPECT_EQ(without_init, (std::array<int, 3>{1, 5, 14}));
  EXPECT_EQ(with_init, (std::array<int, 3>{11, 15, 24}));

  // transform inclusive 先变换当前项再纳入当前前缀；显式 init 在所有变换项之前参与。
}

TEST(AdjacentDifference, FirstOutputIsCopiedThenPairsUseCurrentAndPrevious) {
  const std::array<int, 5> cumulative{3, 8, 15, 24, 35};
  std::array<int, 5> differences{};

  auto end = std::adjacent_difference(
      cumulative.begin(), cumulative.end(), differences.begin());

  EXPECT_EQ(end, differences.end());
  EXPECT_EQ(differences, (std::array<int, 5>{3, 5, 7, 9, 11}));

  // 首项原样复制；之后计算 current-previous，参数方向不能反过来。空输入不写输出。
}

TEST(AdjacentDifference, CustomOperationCanComputeAdjacentRatios) {
  const std::array<int, 4> values{2, 6, 24, 120};
  std::array<int, 4> ratios{};

  std::adjacent_difference(
      values.begin(),
      values.end(),
      ratios.begin(),
      [](int current, int previous) {
        return current / previous;
      });

  EXPECT_EQ(ratios, (std::array<int, 4>{2, 3, 4, 5}));
}

TEST(AdjacentDifference, InPlaceDifferenceAndPartialSumCanRoundTrip) {
  const std::array<int, 5> original{2, 5, 9, 14, 20};
  auto values = original;

  std::adjacent_difference(
      values.begin(), values.end(), values.begin());
  EXPECT_EQ(values, (std::array<int, 5>{2, 3, 4, 5, 6}));

  std::partial_sum(values.begin(), values.end(), values.begin());
  EXPECT_EQ(values, original);

  // 非 policy adjacent_difference 会在覆盖前保存 previous，明确支持原地输出；policy
  // overload 则要求输入输出不重叠。
}

TEST(Iota, ItAssignsThenIncrementsACopyOfTheStartingValue) {
  std::array<int, 5> values{};
  int start = 7;

  std::iota(values.begin(), values.end(), start);

  EXPECT_EQ(values, (std::array<int, 5>{7, 8, 9, 10, 11}));
  EXPECT_EQ(start, 7);

  // value 按值传入：每个位置先赋当前 value，再执行 ++value；调用者的 start 不变。
}

TEST(Iota, EmptyRangePerformsNoAssignmentsOrObservableIncrement) {
  std::vector<int> empty;

  std::iota(empty.begin(), empty.end(), 99);

  EXPECT_TRUE(empty.empty());

  // iota 返回 void，不提供尾 iterator；目标必须预先存在，它不会像 back_inserter 那样
  // 推断数量或扩容。C++20 也没有 std::ranges::iota 算法，views::iota 是惰性 range。
}

#if defined(__GLIBCXX__)

TEST(ParallelScan, SeparateOutputAndPureOperationAvoidOverlapAndDataRaces) {
  const std::array<int, 5> input{1, 2, 3, 4, 5};
  std::array<int, 5> output{};

  std::inclusive_scan(
      std::execution::par,
      input.begin(),
      input.end(),
      output.begin(),
      std::plus<>{});

  EXPECT_EQ(output, (std::array<int, 5>{1, 3, 6, 10, 15}));

  // 测试只断言数学结果，不假设线程数量或调用顺序；整数 plus 可安全重组。
}

#else

TEST(ParallelScan, HostLibcxxIndexingGapDoesNotChangeTheGccBaseline) {
  GTEST_SKIP() << "当前 Apple libc++ 未暴露 C++20 execution policy 对象";
}

#endif

}  // namespace
