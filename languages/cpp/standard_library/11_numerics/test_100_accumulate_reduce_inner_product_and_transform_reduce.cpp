// polyglot-covers:
// - cpp.stdlib.numeric.accumulate-left-fold-and-empty-init
// - cpp.stdlib.numeric.accumulate-initial-value-controls-result-type
// - cpp.stdlib.numeric.accumulate-cpp20-moves-accumulator
// - cpp.stdlib.numeric.reduce-default-init-and-generalized-sum
// - cpp.stdlib.numeric.reduce-unspecified-order-associativity-requirement
// - cpp.stdlib.numeric.inner-product-two-range-contract-and-order
// - cpp.stdlib.numeric.inner-product-custom-transform-and-fold
// - cpp.stdlib.numeric.transform-reduce-binary-dot-product
// - cpp.stdlib.numeric.transform-reduce-unary-transform-before-reduction
// - cpp.stdlib.numeric.transform-reduce-does-not-transform-init
// - cpp.stdlib.numeric.parallel-reduction-order-and-race-safety
// - cpp.stdlib.numeric.cpp20-numeric-algorithms-have-no-ranges-overloads

#include <gtest/gtest.h>

#include <array>
#include <execution>
#include <functional>
#include <numeric>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(Accumulate, ItIsAnOrderedLeftFoldStartingFromInit) {
  const std::array<int, 4> values{1, 2, 3, 4};

  const int difference = std::accumulate(
      values.begin(), values.end(), 20, std::minus<>{});

  EXPECT_EQ(difference, 10);

  // accumulate 严格按顺序执行 `acc = op(move(acc), *i)`，这里是
  // (((20-1)-2)-3)-4。非结合操作需要这种顺序语义时不能换成 reduce。
}

TEST(Accumulate, EmptyRangeReturnsTheInitialValueWithoutCallingTheOperation) {
  const std::vector<int> empty;
  int calls = 0;

  const int result = std::accumulate(
      empty.begin(), empty.end(), 42, [&calls](int left, int right) {
        ++calls;
        return left + right;
      });

  EXPECT_EQ(result, 42);
  EXPECT_EQ(calls, 0);

  // init 既定义空范围结果，也参与决定 accumulator 类型。
}

TEST(Accumulate, InitialValueTypeControlsEveryIntermediateAssignment) {
  const std::array<double, 2> values{0.5, 1.5};

  const auto truncated = std::accumulate(values.begin(), values.end(), 0);
  const auto precise = std::accumulate(values.begin(), values.end(), 0.0);

  static_assert(std::is_same_v<decltype(truncated), const int>);
  static_assert(std::is_same_v<decltype(precise), const double>);
  EXPECT_EQ(truncated, 1);
  EXPECT_DOUBLE_EQ(precise, 2.0);

  // init=0 让 T 成为 int，每一步 double 和都会重新赋给 int 并截断；不是只在最终结果
  // 截断一次。数值累计应主动写出正确 init 类型，如 0.0 或明确的宽整数。
}

TEST(Accumulate, Cpp20MovesTheAccumulatorIntoEachOperation) {
  const std::array<std::string, 3> parts{"C++", "20", "tests"};
  int calls = 0;

  auto joined = std::accumulate(
      parts.begin(),
      parts.end(),
      std::string{},
      [&calls](std::string accumulator, const std::string& part) {
        ++calls;
        if (!accumulator.empty()) {
          accumulator += '/';
        }
        accumulator += part;
        return accumulator;
      });

  EXPECT_EQ(joined, "C++/20/tests");
  EXPECT_EQ(calls, 3);

  // C++20 明确把 accumulator 以 std::move(acc) 传入，允许复用其缓冲区；操作仍必须
  // 返回可赋给 T 的结果，并不得修改输入元素或使 iterator 失效。
}

TEST(Reduce, DefaultInitialValueIsValueInitializedElementType) {
  const std::array<int, 4> values{1, 2, 3, 4};

  EXPECT_EQ(std::reduce(values.begin(), values.end()), 10);
  EXPECT_EQ(std::reduce(values.begin(), values.end(), 100), 110);

  // 无 init overload 使用 iterator value_type{}，对 int 即 0。显式 init 同样参与
  // generalized sum，但 reduce 可以用未指定的分组和顺序组合各项。
}

TEST(Reduce, UseAnAssociativeCommutativeOperationWhenOrderMustNotMatter) {
  const std::array<unsigned, 5> flags{0x01U, 0x10U, 0x04U, 0x01U, 0x20U};

  const unsigned combined = std::reduce(
      flags.begin(), flags.end(), 0U, std::bit_or<>{});

  EXPECT_EQ(combined, 0x35U);

  // bit_or 具结合性和交换性，任意分组/重排都给相同结果。减法、字符串拼接或浮点加法
  // 若要求逐步可复现，不适合 reduce；浮点舍入可能随实现和并行分组改变。
}

TEST(InnerProduct, FirstRangeLengthDefinesHowMuchOfTheSecondRangeIsRead) {
  const std::array<int, 3> weights{2, 3, 5};
  const std::array<int, 5> values{10, 20, 30, 999, 999};

  const int dot = std::inner_product(
      weights.begin(), weights.end(), values.begin(), 0);

  EXPECT_EQ(dot, 230);

  // inner_product 只接第二路 begin，默认第二路至少与第一路一样长；多余项忽略，过短
  // 会越界。计算按第一路顺序折叠，默认是 acc + left*right。
}

TEST(InnerProduct, CustomOperationsCanExpressPairwiseDistanceAccumulation) {
  const std::array<int, 3> left{1, 5, 9};
  const std::array<int, 3> right{4, 1, 7};

  const int distance = std::inner_product(
      left.begin(),
      left.end(),
      right.begin(),
      0,
      std::plus<>{},
      [](int first, int second) {
        return first > second ? first - second : second - first;
      });

  EXPECT_EQ(distance, 9);

  // binary_op2 先把每对输入转成距离，binary_op1 再按顺序累计；两个 callable 都不得
  // 修改输入或使遍历失效。
}

TEST(TransformReduce, BinaryFormCombinesPairwiseTransformWithGeneralizedReduction) {
  const std::array<int, 3> left{1, 2, 3};
  const std::array<int, 3> right{4, 5, 6};

  const int dot = std::transform_reduce(
      left.begin(), left.end(), right.begin(), 10);

  EXPECT_EQ(dot, 42);

  // 默认二元形式把乘积 generalized-sum 到 init，等价结果是 10+1*4+2*5+3*6；
  // 与 inner_product 不同，它允许重新分组，操作应满足相应可组合要求。
}

TEST(TransformReduce, UnaryFormTransformsEveryInputBeforeReduction) {
  const std::array<int, 4> values{-1, 2, -3, 4};

  const int squared_sum = std::transform_reduce(
      values.begin(),
      values.end(),
      0,
      std::plus<>{},
      [](int value) {
        return value * value;
      });

  EXPECT_EQ(squared_sum, 30);

  // unary_op 对每个输入项执行，binary_op 归约变换结果；不需要创建 squares 临时容器。
}

TEST(TransformReduce, InitialValueIsNotPassedThroughTheUnaryTransform) {
  const std::array<int, 2> values{2, 3};

  const int result = std::transform_reduce(
      values.begin(),
      values.end(),
      10,
      std::plus<>{},
      [](int value) {
        return value * value;
      });

  EXPECT_EQ(result, 23);

  // 结果是 init 10 加 4 和 9，而不是先把 init 也平方；这是条文特别指出的边界。
}

#if defined(__GLIBCXX__)

TEST(ParallelReduce, CallbackUsesOrderIndependentPureOperations) {
  const std::vector<int> values{1, 2, 3, 4, 5, 6};

  const int sum = std::reduce(
      std::execution::par, values.begin(), values.end(), 0, std::plus<>{});
  const int squared_sum = std::transform_reduce(
      std::execution::par,
      values.begin(),
      values.end(),
      0,
      std::plus<>{},
      [](int value) noexcept {
        return value * value;
      });

  EXPECT_EQ(sum, 21);
  EXPECT_EQ(squared_sum, 91);

  // par 不保证一定创建线程；纯变换和整数加法不共享可变状态，也不依赖调用次序。
}

#else

TEST(ParallelReduce, HostLibcxxIndexingGapDoesNotChangeTheGccBaseline) {
  GTEST_SKIP() << "当前 Apple libc++ 未暴露 C++20 execution policy 对象";
}

#endif

TEST(NumericAlgorithms, Cpp20DoesNotProvideRangesCounterparts) {
  SUCCEED();

  // C++20 的 accumulate/reduce/scan 等只提供 iterator 接口，没有 std::ranges 版本；
  // 不要因其他算法已有 ranges CPO 就臆造 std::ranges::accumulate。可传 begin/end，或
  // 在后续标准/第三方范围算法明确可用时再选择对应接口。
}

}  // namespace
