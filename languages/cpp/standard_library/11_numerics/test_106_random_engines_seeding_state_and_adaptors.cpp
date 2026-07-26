// polyglot-covers:
// - cpp.stdlib.random.urbg-range-state-and-copy-semantics
// - cpp.stdlib.random.linear-congruential-engine-and-minstd-aliases
// - cpp.stdlib.random.mersenne-twister-portable-sequence
// - cpp.stdlib.random.subtract-with-carry-and-ranlux-aliases
// - cpp.stdlib.random.engine-seed-reset-discard-and-equality
// - cpp.stdlib.random.engine-stream-state-round-trip
// - cpp.stdlib.random.seed-seq-generation-param-and-engine-seeding
// - cpp.stdlib.random.discard-block-independent-bits-and-shuffle-adaptors
// - cpp.stdlib.random.generate-canonical-half-open-unit-interval
// - cpp.stdlib.random.random-device-nondeterministic-seed-boundary
// - cpp.stdlib.random.default-random-engine-implementation-choice
// - cpp.stdlib.random.c-rand-global-state-and-repeatability-limit

#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <cstdlib>
#include <iterator>
#include <limits>
#include <random>
#include <sstream>
#include <type_traits>
#include <vector>

namespace {

template <class Engine, std::size_t Size>
std::array<typename Engine::result_type, Size> Draw(Engine& engine) {
  std::array<typename Engine::result_type, Size> values{};
  for (auto& value : values) {
    value = engine();
  }
  return values;
}

TEST(RandomEngineRequirements, EnginesExposeAnInclusiveUnsignedResultRange) {
  static_assert(std::is_unsigned_v<std::mt19937::result_type>);
  static_assert(std::mt19937::min() < std::mt19937::max());

  std::mt19937 engine{123U};
  for (int index = 0; index < 10; ++index) {
    const auto value = engine();
    EXPECT_GE(value, std::mt19937::min());
    EXPECT_LE(value, std::mt19937::max());
  }

  // UniformRandomBitGenerator 的 min/max 都包含在输出范围内。引擎产生的是均匀比特，
  // 不是任意业务区间；把 `% n` 当分布会在范围大小不能整除 n 时引入模偏差。
}

TEST(RandomEngineState, EqualCopiesContinueWithTheSameSequence) {
  std::mt19937 original{2024U};
  static_cast<void>(original());
  std::mt19937 copy = original;

  EXPECT_EQ(original, copy);
  EXPECT_EQ((Draw<std::mt19937, 8>(original)),
            (Draw<std::mt19937, 8>(copy)));
  EXPECT_EQ(original, copy);

  // 拷贝保存完整内部状态，适合复现实验分支；它并不会产生“独立随机流”。需要独立流时
  // 应设计明确的 seed 派生方案。
}

TEST(RandomEngineState, SeedRestartsAndDiscardAdvancesWithoutReturningValues) {
  constexpr std::uint32_t seed = 77U;
  std::mt19937 engine{seed};
  const auto first_run = Draw<std::mt19937, 4>(engine);

  engine.seed(seed);
  EXPECT_EQ((Draw<std::mt19937, 4>(engine)), first_run);

  std::mt19937 discarded{seed};
  std::mt19937 manually_advanced{seed};
  discarded.discard(3);
  static_cast<void>(manually_advanced());
  static_cast<void>(manually_advanced());
  static_cast<void>(manually_advanced());
  EXPECT_EQ(discarded(), manually_advanced());
}

TEST(LinearCongruentialEngine, StandardAliasHasAPortableFirstValue) {
  std::minstd_rand engine{1U};

  EXPECT_EQ(engine(), 48271U);
  static_assert(std::minstd_rand::multiplier == 48271U);
  static_assert(std::minstd_rand::increment == 0U);
  static_assert(std::minstd_rand::modulus == 2147483647U);

  // 预定义别名锁定了参数和转换算法，所以给定种子的序列可跨标准实现复现；这不等于
  // 该老式线性同余引擎适合密码学。
}

TEST(MersenneTwisterEngine, StandardParametersProduceAPortableSequence) {
  std::mt19937 engine;

  EXPECT_EQ(engine(), 3499211612U);
  EXPECT_EQ(engine(), 581869302U);
  static_assert(std::mt19937::word_size == 32U);
  static_assert(std::mt19937::state_size == 624U);

  // mt19937 的默认种子、参数和状态转移由标准锁定。它周期长且适合模拟，但观察足够
  // 输出可恢复状态，不能用于令牌、密码或其他对抗性场景。
}

TEST(SubtractWithCarryEngine, RanluxBaseAndAdaptorAreDistinctEngineLayers) {
  std::ranlux24_base base{42U};
  std::ranlux24 luxury{42U};

  const auto base_values = Draw<std::ranlux24_base, 5>(base);
  const auto luxury_values = Draw<std::ranlux24, 5>(luxury);

  EXPECT_EQ(base_values.front(), luxury_values.front());
  static_assert(std::ranlux24_base::word_size == 24U);
  static_assert(std::ranlux24::block_size == 223U);
  static_assert(std::ranlux24::used_block == 23U);

  // ranlux24 在 subtract_with_carry 基础引擎外套 discard_block_engine；初始输出可相同，
  // 到块边界后适配器会丢弃一部分底层值。
}

TEST(RandomEngineStreaming, TextRoundTripPreservesTheExactContinuationState) {
  std::mt19937 source{91U};
  source.discard(17);

  std::ostringstream output;
  output << source;
  ASSERT_TRUE(output);

  std::mt19937 restored;
  std::istringstream input{output.str()};
  input >> restored;

  ASSERT_TRUE(input);
  EXPECT_EQ(restored, source);
  EXPECT_EQ((Draw<std::mt19937, 6>(restored)),
            (Draw<std::mt19937, 6>(source)));

  // 流格式用于同一种引擎类型的状态往返，不应作为人工编辑的稳定跨版本数据协议。
}

TEST(SeedSequence, ParamReturnsTheOriginalConstructionMaterial) {
  std::seed_seq sequence{1U, 2U, 3U, 0xFFFF'FFFFU};
  std::vector<std::uint32_t> parameters;
  sequence.param(std::back_inserter(parameters));

  EXPECT_EQ(sequence.size(), 4U);
  EXPECT_EQ(parameters,
            (std::vector<std::uint32_t>{1U, 2U, 3U, 0xFFFF'FFFFU}));

  // seed_seq 会把输入转换到 uint_least32_t 的无符号范围；param 返回构造材料，而不是
  // generate 扩散后的内部输出。
}

TEST(SeedSequence, EqualMaterialGeneratesEqualDiffusedWords) {
  std::seed_seq first{1U, 2U, 3U};
  std::seed_seq second{1U, 2U, 3U};
  std::seed_seq different{1U, 2U, 4U};
  std::array<std::uint32_t, 8> first_words{};
  std::array<std::uint32_t, 8> second_words{};
  std::array<std::uint32_t, 8> different_words{};

  first.generate(first_words.begin(), first_words.end());
  second.generate(second_words.begin(), second_words.end());
  different.generate(different_words.begin(), different_words.end());

  EXPECT_EQ(first_words, second_words);
  EXPECT_NE(first_words, different_words);
  static_assert(!std::is_copy_constructible_v<std::seed_seq>);

  // seed_seq 是可重复的扩散器，不是熵源；它故意不可复制，但用同样材料重建即可得到
  // 同样输出。
}

TEST(SeedSequence, EnginesCanConsumeMoreSeedStateThanOneIntegerProvides) {
  std::seed_seq first_seed{10U, 20U, 30U, 40U};
  std::seed_seq second_seed{10U, 20U, 30U, 40U};
  std::mt19937 first{first_seed};
  std::mt19937 second{second_seed};

  EXPECT_EQ((Draw<std::mt19937, 10>(first)),
            (Draw<std::mt19937, 10>(second)));

  // mt19937 内部有 624 个状态字。单个 32 位 seed 只能选择有限的一小部分状态；
  // seed_seq 可把多个种子字扩散到引擎所需的完整状态材料。
}

TEST(RandomAdaptor, DiscardBlockMatchesManualKeepAndDiscardScheduling) {
  using Base = std::minstd_rand;
  using Adapted = std::discard_block_engine<Base, 5, 2>;
  Adapted adapted{Base{7U}};
  Base manual{7U};

  EXPECT_EQ(adapted(), manual());
  EXPECT_EQ(adapted(), manual());
  manual.discard(3);
  EXPECT_EQ(adapted(), manual());
  EXPECT_EQ(adapted(), manual());

  // 每个底层长度为 p 的块只暴露前 r 个值；适配器的状态包括底层引擎和当前块位置。
}

TEST(RandomAdaptor, IndependentBitsBuildsAFixedWidthUnsignedResult) {
  using EightBits = std::independent_bits_engine<std::mt19937, 8, std::uint16_t>;
  EightBits engine{std::mt19937{9U}};

  for (int index = 0; index < 20; ++index) {
    EXPECT_LE(engine(), 255U);
  }
  static_assert(EightBits::min() == 0U);
  static_assert(EightBits::max() == 255U);

  // independent_bits_engine 组合底层输出，产生精确 w 位的无符号结果；它不是“把结果
  // 截断到低八位”的简单别名。
}

TEST(RandomAdaptor, ShuffleOrderIsDeterministicForEqualBaseStates) {
  using Shuffled = std::shuffle_order_engine<std::minstd_rand, 32>;
  Shuffled first{std::minstd_rand{12U}};
  Shuffled second{std::minstd_rand{12U}};

  EXPECT_EQ((Draw<Shuffled, 12>(first)), (Draw<Shuffled, 12>(second)));
  static_assert(Shuffled::table_size == 32U);

  // shuffle_order_engine 用表格重新排列底层序列，仍是确定性引擎而非额外熵源。
}

TEST(RandomUtility, GenerateCanonicalProducesTheHalfOpenUnitInterval) {
  std::mt19937 engine{1234U};

  for (int index = 0; index < 20; ++index) {
    const double value = std::generate_canonical<double, 53>(engine);
    EXPECT_GE(value, 0.0);
    EXPECT_LT(value, 1.0);
  }

  // 第二个模板参数是期望的随机位数上限；函数可能调用引擎多次，并保证结果在 [0,1)。
}

TEST(RandomDevice, ItIsAnExternalBoundaryNotAReproducibleTestEngine) {
  static_assert(std::is_same_v<std::random_device::result_type, unsigned int>);
  EXPECT_LT(std::random_device::min(), std::random_device::max());

  // random_device 可以访问非确定性设备，也允许在设备不可用时采用实现定义的伪随机源。
  // entropy() 甚至可以返回 0；因此测试不实例化它、不比较两次输出，也不把它用作可复现
  // 测试序列。实际程序可在外部边界取种子，再记录种子以便重放。
}

TEST(DefaultRandomEngine, AliasChoiceIsImplementationDefined) {
  std::default_random_engine first{33U};
  std::default_random_engine second{33U};

  EXPECT_EQ((Draw<std::default_random_engine, 6>(first)),
            (Draw<std::default_random_engine, 6>(second)));

  // 同一实现内给定种子仍可重复，但 default_random_engine 的具体类型由实现选择。需要
  // 跨平台固定序列时应直接命名 mt19937、minstd_rand 等标准别名。
}

TEST(LowQualityRandom, CApiOnlyPromisesRepeatabilityWithinOneImplementation) {
  std::srand(123);
  const int first = std::rand();
  const int second = std::rand();
  std::srand(123);

  EXPECT_EQ(std::rand(), first);
  EXPECT_EQ(std::rand(), second);

  // rand/srand 使用进程级共享状态，算法也由实现决定；它不适合并发组件、跨平台重现或
  // 无偏分布。现代代码应把显式引擎对象作为依赖传递。
}

}  // namespace
