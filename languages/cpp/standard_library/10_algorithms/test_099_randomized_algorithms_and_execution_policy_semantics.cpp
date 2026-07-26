// polyglot-covers:
// - cpp.stdlib.algorithms.shuffle-permutation-and-urbg
// - cpp.stdlib.algorithms.seeded-shuffle-reproducibility-boundary
// - cpp.stdlib.algorithms.ranges-shuffle-returned-end
// - cpp.stdlib.algorithms.sample-size-subset-and-source-order
// - cpp.stdlib.algorithms.sample-large-count-and-zero-boundaries
// - cpp.stdlib.algorithms.random-device-versus-seeded-engine-testing
// - cpp.stdlib.algorithms.execution-policy-type-traits
// - cpp.stdlib.algorithms.sequenced-policy-and-policy-overload-return
// - cpp.stdlib.algorithms.parallel-policy-element-independence
// - cpp.stdlib.algorithms.parallel-unsequenced-vectorization-safety
// - cpp.stdlib.algorithms.execution-policy-exception-termination

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <execution>
#include <numeric>
#include <random>
#include <ranges>
#include <type_traits>
#include <vector>

namespace {

TEST(Shuffle, ItProducesAPermutationUsingTheSuppliedUniformRandomBitGenerator) {
  const std::array<int, 8> original{1, 2, 3, 4, 5, 6, 7, 8};
  auto values = original;
  std::mt19937 engine{0xC0FFEEU};

  std::shuffle(values.begin(), values.end(), engine);

  EXPECT_TRUE(std::ranges::is_permutation(values, original));

  // shuffle 只保证得到原元素的某个等概率排列，不保证特定 seed 跨不同标准库版本产生
  // 同一排列，且原排列本身也是合法结果；测试应验证 permutation，而不是硬编码或要求
  // 结果一定改变。
}

TEST(Shuffle, EqualEngineStateIsReproducibleWithinTheSameImplementation) {
  std::array<int, 10> first{0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
  auto second = first;
  std::mt19937 first_engine{12345U};
  std::mt19937 second_engine{12345U};

  std::ranges::shuffle(first, first_engine);
  std::ranges::shuffle(second, second_engine);

  EXPECT_EQ(first, second);
  EXPECT_EQ(first_engine, second_engine);

  // 相同程序、相同 URBG 初始状态会走相同随机选择，适合复现本次失败；但标准没有锁定
  // shuffle 如何把 URBG 输出映射为交换位置，不能把排列写成跨实现持久格式。
}

TEST(RangesShuffle, ItReturnsTheFinalIteratorAndHandlesTrivialRanges) {
  std::vector<int> values{1, 2, 3, 4};
  std::vector<int> empty;
  std::array<int, 1> singleton{42};
  std::mt19937 engine{7U};

  auto end = std::ranges::shuffle(values, engine);
  auto empty_end = std::ranges::shuffle(empty, engine);
  auto singleton_end = std::ranges::shuffle(singleton, engine);

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(empty_end, empty.end());
  EXPECT_EQ(singleton_end, singleton.end());
  EXPECT_TRUE(std::ranges::is_permutation(values, std::array{1, 2, 3, 4}));

  // ranges::shuffle 要求随机访问且可置换的 range；返回 borrowed iterator 或 dangling。
}

TEST(Sample, ItSelectsTheRequestedSubsetWithoutChangingThePopulation) {
  const std::vector<int> population{1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
  std::vector<int> selected;
  std::mt19937 engine{2024U};

  auto output_end = std::sample(
      population.begin(),
      population.end(),
      std::back_inserter(selected),
      4,
      engine);
  *output_end = 99;

  ASSERT_EQ(selected.size(), 5U);
  EXPECT_TRUE(std::is_sorted(selected.begin(), selected.end() - 1));
  for (auto iterator = selected.begin(); iterator != selected.end() - 1; ++iterator) {
    EXPECT_TRUE(std::ranges::binary_search(population, *iterator));
  }
  EXPECT_EQ(selected.back(), 99);
  EXPECT_EQ(population, (std::vector<int>{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}));

  // ForwardIterator 输入会保持被抽中元素的源相对顺序；sample 返回输出尾。不同输入
  // iterator 类别可采用不同抽样策略，测试不应锁定具体样本值。
}

TEST(Sample, RequestedCountIsClampedToPopulationSize) {
  const std::array<int, 3> population{10, 20, 30};
  std::vector<int> selected;
  std::mt19937 engine{1U};

  std::sample(
      population.begin(),
      population.end(),
      std::back_inserter(selected),
      10,
      engine);

  EXPECT_EQ(selected, (std::vector<int>{10, 20, 30}));

  // n 大于 population 长度时输出全部元素；n 必须非负。输出 iterator 必须能容纳
  // min(n,distance) 项，back_inserter 才会自动扩容。
}

TEST(Sample, ZeroCountProducesNoOutput) {
  const std::array<int, 4> population{1, 2, 3, 4};
  std::vector<int> selected;
  std::mt19937 engine{9U};

  auto end = std::sample(
      population.begin(),
      population.end(),
      std::back_inserter(selected),
      0,
      engine);

  EXPECT_TRUE(selected.empty());
  *end = 5;
  EXPECT_EQ(selected, (std::vector<int>{5}));
}

TEST(RandomizedTesting, SeededEngineSeparatesReproductionFromEntropyAcquisition) {
  std::mt19937 reproducible{42U};
  auto first = reproducible();
  std::mt19937 replay{42U};

  EXPECT_EQ(first, replay());

  // random_device 用于尝试获取非确定性 seed，其实现也可能退化为伪随机；单元测试不能
  // 断言它每次不同。测试固定 seed，生产代码若需熵再在边界处注入 random_device。
}

#if defined(__GLIBCXX__)

TEST(ExecutionPolicies, StandardPolicyObjectsAreRecognizedByTheTrait) {
  static_assert(std::is_execution_policy_v<
                std::remove_cvref_t<decltype(std::execution::seq)>>);
  static_assert(std::is_execution_policy_v<
                std::remove_cvref_t<decltype(std::execution::par)>>);
  static_assert(std::is_execution_policy_v<
                std::remove_cvref_t<decltype(std::execution::par_unseq)>>);
  static_assert(std::is_execution_policy_v<
                std::remove_cvref_t<decltype(std::execution::unseq)>>);

  SUCCEED();

  // C++20 有 seq、par、par_unseq、unseq；它们选择允许的执行与向量化约束，不承诺
  // 某次调用一定创建线程或获得加速，实现可以退化为串行执行。
}

TEST(SequencedPolicy, ForEachPolicyOverloadReturnsVoidInsteadOfFunctionState) {
  std::array<int, 4> values{1, 2, 3, 4};
  auto increment = [](int& value) {
    ++value;
  };

  static_assert(std::is_same_v<
                decltype(std::for_each(
                    std::execution::seq,
                    values.begin(),
                    values.end(),
                    increment)),
                void>);

  std::for_each(
      std::execution::seq, values.begin(), values.end(), increment);
  EXPECT_EQ(values, (std::array<int, 4>{2, 3, 4, 5}));

  // 普通 for_each 返回最终函数对象，policy overload 返回 void；不能靠取回 functor
  // 状态汇总结果。seq 禁止并行执行，但仍应把算法结果写到明确输出或外部安全状态。
}

TEST(ParallelPolicy, IndependentOutputSlotsAvoidDataRacesAndThreadAssumptions) {
  const std::vector<int> input{1, 2, 3, 4, 5, 6};
  std::vector<int> output(input.size());

  std::transform(
      std::execution::par,
      input.begin(),
      input.end(),
      output.begin(),
      [](int value) {
        return value * value;
      });

  EXPECT_EQ(output, (std::vector<int>{1, 4, 9, 16, 25, 36}));

  // 每次调用只读独立输入并写独立输出槽，没有数据竞争；测试不记录 thread id，也不以
  // 耗时判断是否“真的并行”，因为调度和后端选择属于实现权限。
}

TEST(ParallelPolicy, AtomicStateCanSupportOrderIndependentAggregation) {
  const std::array<int, 5> values{1, 2, 3, 4, 5};
  std::atomic<int> sum{0};

  std::for_each(
      std::execution::par,
      values.begin(),
      values.end(),
      [&sum](int value) {
        sum.fetch_add(value, std::memory_order_relaxed);
      });

  EXPECT_EQ(sum.load(std::memory_order_relaxed), 15);

  // 普通 int 累加在并行执行时会产生数据竞争；原子可表达与顺序无关的整数聚合。浮点
  // 聚合即使无数据竞争，也可能因结合顺序变化产生不同舍入结果。
}

TEST(ParallelUnsequencedPolicy, CallbackUsesOnlyVectorizationSafeElementWork) {
  const std::array<int, 6> input{1, 2, 3, 4, 5, 6};
  std::array<int, 6> output{};

  std::transform(
      std::execution::par_unseq,
      input.begin(),
      input.end(),
      output.begin(),
      [](int value) noexcept {
        return value * 3;
      });

  EXPECT_EQ(output, (std::array<int, 6>{3, 6, 9, 12, 15, 18}));

  // par_unseq 允许不同线程并行，也允许同一线程内调用交错/向量化；回调不应使用 mutex、
  // 阻塞同步、动态分配等 vectorization-unsafe 操作。这里是纯逐元素计算。
}

TEST(UnsequencedPolicy, ItAllowsVectorizationWithoutPromisingParallelThreads) {
  std::array<int, 4> values{1, 2, 3, 4};

  std::for_each(
      std::execution::unseq,
      values.begin(),
      values.end(),
      [](int& value) noexcept {
        value = -value;
      });

  EXPECT_EQ(values, (std::array<int, 4>{-1, -2, -3, -4}));

  // unseq 允许在调用线程内以不定次序和向量化方式执行，不允许多个线程并行；不同元素
  // 的副作用仍不能互相依赖。
}

TEST(ExecutionPolicies, ThrowingCallbacksAreDocumentedWithoutExecutingTermination) {
  SUCCEED();

  // 对标准 execution policy 的算法调用，若元素函数抛出异常，标准要求调用
  // std::terminate；这不能用普通 EXPECT_THROW 验证。实际代码应让回调不抛，或在回调
  // 内捕获并通过并发安全通道报告错误；本仓库不执行会终止整个测试进程的示例。
}

#else

TEST(ExecutionPolicies, HostLibcxxIndexingGapIsKeptSeparateFromTheGccBaseline) {
  GTEST_SKIP() << "当前 Apple libc++ 未暴露 C++20 execution policy 对象";

  // 这个分支只让主机 clangd 能完整索引文件；仓库权威 GCC/libstdc++ 基线走上方分支并
  // 实际运行全部策略案例。不能因阅读端标准库缺失而删除目标工具链具备的标准能力。
}

#endif

}  // namespace
