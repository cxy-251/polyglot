// polyglot-covers:
// - cpp.stdlib.random.distribution-engine-separation-and-nonportable-mapping
// - cpp.stdlib.random.distribution-param-object-temporary-override-and-reset
// - cpp.stdlib.random.uniform-int-and-uniform-real-half-open-boundaries
// - cpp.stdlib.random.bernoulli-binomial-geometric-and-negative-binomial
// - cpp.stdlib.random.poisson-exponential-gamma-weibull-and-extreme-value
// - cpp.stdlib.random.normal-lognormal-chi-squared-cauchy-fisher-f-student-t
// - cpp.stdlib.random.discrete-distribution-normalized-weights
// - cpp.stdlib.random.piecewise-constant-interval-densities
// - cpp.stdlib.random.piecewise-linear-knot-densities
// - cpp.stdlib.random.distribution-stream-state-round-trip
// - cpp.stdlib.random.deterministic-sampling-workflow-and-statistical-tolerance

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <numeric>
#include <random>
#include <sstream>
#include <type_traits>
#include <vector>

namespace {

template <class Distribution, class Predicate>
void ExpectSamplesSatisfy(Distribution& distribution,
                          std::mt19937& engine,
                          int count,
                          Predicate predicate) {
  for (int index = 0; index < count; ++index) {
    EXPECT_TRUE(predicate(distribution(engine)));
  }
}

TEST(RandomDistributionModel, EngineAndDistributionHaveSeparateResponsibilities) {
  std::mt19937 first_engine{123U};
  std::mt19937 second_engine{123U};
  std::uniform_int_distribution<int> die{1, 6};
  std::uniform_real_distribution<double> unit{0.0, 1.0};

  EXPECT_EQ(first_engine(), second_engine());
  second_engine.seed(123U);

  const int die_roll = die(first_engine);
  const double fraction = unit(second_engine);
  EXPECT_GE(die_roll, 1);
  EXPECT_LE(die_roll, 6);
  EXPECT_GE(fraction, 0.0);
  EXPECT_LT(fraction, 1.0);

  // 引擎定义可复现的均匀整数流，分布把该流映射为目标统计模型。标准锁定引擎序列，
  // 通常不锁定分布采用的映射算法，所以相同引擎状态跨实现未必得到相同分布样本。
}

TEST(UniformDistributions, IntegerBoundsAreClosedAndRealUpperBoundIsExcluded) {
  std::mt19937 engine{7U};
  std::uniform_int_distribution<int> integers{-2, 2};
  std::uniform_real_distribution<double> reals{-2.0, 2.0};

  ExpectSamplesSatisfy(integers, engine, 100, [](int value) {
    return value >= -2 && value <= 2;
  });
  ExpectSamplesSatisfy(reals, engine, 100, [](double value) {
    return value >= -2.0 && value < 2.0;
  });

  EXPECT_EQ(integers.a(), -2);
  EXPECT_EQ(integers.b(), 2);
  EXPECT_DOUBLE_EQ(reals.a(), -2.0);
  EXPECT_DOUBLE_EQ(reals.b(), 2.0);

  // uniform_int_distribution 是闭区间 [a,b]；uniform_real_distribution 的常规语义
  // 是半开区间 [a,b)。两者边界不能按同一种规则写验证。
}

TEST(DistributionParameters, ParamObjectCanTemporarilyOverrideStoredParameters) {
  std::mt19937 engine{11U};
  std::uniform_int_distribution<int> distribution{1, 6};
  const std::uniform_int_distribution<int>::param_type forced{9, 9};

  EXPECT_EQ(distribution(engine, forced), 9);
  EXPECT_EQ(distribution.a(), 1);
  EXPECT_EQ(distribution.b(), 6);

  distribution.param(forced);
  EXPECT_EQ(distribution.a(), 9);
  EXPECT_EQ(distribution.b(), 9);
  EXPECT_EQ(distribution(engine), 9);

  // operator(engine,param) 只为本次调用覆盖参数；param(p) 才修改分布保存的参数。
}

TEST(BernoulliFamily, DegenerateProbabilityEndpointsAreDeterministic) {
  std::mt19937 engine{19U};
  std::bernoulli_distribution never{0.0};
  std::bernoulli_distribution always{1.0};

  for (int index = 0; index < 20; ++index) {
    EXPECT_FALSE(never(engine));
    EXPECT_TRUE(always(engine));
  }
  EXPECT_DOUBLE_EQ(never.p(), 0.0);
  EXPECT_DOUBLE_EQ(always.p(), 1.0);
}

TEST(BernoulliFamily, CountingDistributionsExposeTheirDefiningParameters) {
  std::mt19937 engine{23U};
  std::binomial_distribution<int> binomial{10, 0.25};
  std::geometric_distribution<int> geometric{0.4};
  std::negative_binomial_distribution<int> negative_binomial{3, 0.4};

  ExpectSamplesSatisfy(binomial, engine, 100, [](int value) {
    return value >= 0 && value <= 10;
  });
  ExpectSamplesSatisfy(geometric, engine, 100, [](int value) {
    return value >= 0;
  });
  ExpectSamplesSatisfy(negative_binomial, engine, 100, [](int value) {
    return value >= 0;
  });

  EXPECT_EQ(binomial.t(), 10);
  EXPECT_DOUBLE_EQ(binomial.p(), 0.25);
  EXPECT_DOUBLE_EQ(geometric.p(), 0.4);
  EXPECT_EQ(negative_binomial.k(), 3);
  EXPECT_DOUBLE_EQ(negative_binomial.p(), 0.4);

  // binomial 统计固定 t 次试验中的成功数；geometric 统计首次成功前的失败数；
  // negative_binomial 统计第 k 次成功前的失败数，三个返回值不是同一种计数。
}

TEST(PoissonFamily, NonnegativeDistributionsKeepTheirSupport) {
  std::mt19937 engine{29U};
  std::poisson_distribution<int> poisson{4.0};
  std::exponential_distribution<double> exponential{2.0};
  std::gamma_distribution<double> gamma{2.0, 3.0};
  std::weibull_distribution<double> weibull{1.5, 2.0};

  ExpectSamplesSatisfy(poisson, engine, 100, [](int value) {
    return value >= 0;
  });
  ExpectSamplesSatisfy(exponential, engine, 100, [](double value) {
    return value >= 0.0;
  });
  ExpectSamplesSatisfy(gamma, engine, 100, [](double value) {
    return value >= 0.0;
  });
  ExpectSamplesSatisfy(weibull, engine, 100, [](double value) {
    return value >= 0.0;
  });

  EXPECT_DOUBLE_EQ(poisson.mean(), 4.0);
  EXPECT_DOUBLE_EQ(exponential.lambda(), 2.0);
  EXPECT_DOUBLE_EQ(gamma.alpha(), 2.0);
  EXPECT_DOUBLE_EQ(gamma.beta(), 3.0);
  EXPECT_DOUBLE_EQ(weibull.a(), 1.5);
  EXPECT_DOUBLE_EQ(weibull.b(), 2.0);
}

TEST(PoissonFamily, ExtremeValueHasUnboundedRealSupport) {
  std::mt19937 engine{31U};
  std::extreme_value_distribution<double> distribution{2.0, 0.5};

  ExpectSamplesSatisfy(distribution, engine, 100, [](double value) {
    return std::isfinite(value);
  });
  EXPECT_DOUBLE_EQ(distribution.a(), 2.0);
  EXPECT_DOUBLE_EQ(distribution.b(), 0.5);

  // extreme_value 的 a 是位置、b 是正尺度，返回值不像同组其他分布那样限制为非负。
}

TEST(NormalFamily, NormalAndLognormalDifferByExponentiation) {
  std::mt19937 engine{37U};
  std::normal_distribution<double> normal{2.0, 3.0};
  std::lognormal_distribution<double> lognormal{2.0, 3.0};

  ExpectSamplesSatisfy(normal, engine, 100, [](double value) {
    return std::isfinite(value);
  });
  ExpectSamplesSatisfy(lognormal, engine, 100, [](double value) {
    return value > 0.0;
  });

  EXPECT_DOUBLE_EQ(normal.mean(), 2.0);
  EXPECT_DOUBLE_EQ(normal.stddev(), 3.0);
  EXPECT_DOUBLE_EQ(lognormal.m(), 2.0);
  EXPECT_DOUBLE_EQ(lognormal.s(), 3.0);

  // lognormal 的 m/s 是底层正态变量的参数，不是最终样本的算术均值和标准差。
}

TEST(NormalFamily, ShapeDistributionsExposeDomainSpecificDegreesOfFreedom) {
  std::mt19937 engine{41U};
  std::chi_squared_distribution<double> chi_squared{4.0};
  std::cauchy_distribution<double> cauchy{1.0, 2.0};
  std::fisher_f_distribution<double> fisher{5.0, 7.0};
  std::student_t_distribution<double> student{9.0};

  ExpectSamplesSatisfy(chi_squared, engine, 100, [](double value) {
    return value >= 0.0;
  });
  ExpectSamplesSatisfy(cauchy, engine, 100, [](double value) {
    return std::isfinite(value);
  });
  ExpectSamplesSatisfy(fisher, engine, 100, [](double value) {
    return value >= 0.0;
  });
  ExpectSamplesSatisfy(student, engine, 100, [](double value) {
    return std::isfinite(value);
  });

  EXPECT_DOUBLE_EQ(chi_squared.n(), 4.0);
  EXPECT_DOUBLE_EQ(cauchy.a(), 1.0);
  EXPECT_DOUBLE_EQ(cauchy.b(), 2.0);
  EXPECT_DOUBLE_EQ(fisher.m(), 5.0);
  EXPECT_DOUBLE_EQ(fisher.n(), 7.0);
  EXPECT_DOUBLE_EQ(student.n(), 9.0);

  // Cauchy 的均值和方差并不存在，不能对所有“看似钟形”的分布套用样本均值收敛直觉。
}

TEST(SamplingDistribution, DiscreteWeightsAreNormalizedIntoProbabilities) {
  std::discrete_distribution<int> distribution{1.0, 2.0, 1.0};
  const auto probabilities = distribution.probabilities();

  ASSERT_EQ(probabilities.size(), 3U);
  EXPECT_NEAR(probabilities[0], 0.25, 1e-15);
  EXPECT_NEAR(probabilities[1], 0.50, 1e-15);
  EXPECT_NEAR(probabilities[2], 0.25, 1e-15);

  std::mt19937 engine{43U};
  std::discrete_distribution<int> forced{0.0, 0.0, 5.0};
  for (int index = 0; index < 20; ++index) {
    EXPECT_EQ(forced(engine), 2);
  }

  // 构造参数是非负权重，不要求预先归一化；结果是权重索引，而不是权重值本身。
}

TEST(SamplingDistribution, PiecewiseConstantUsesOneDensityPerInterval) {
  const std::array<double, 3> boundaries{0.0, 1.0, 3.0};
  const std::array<double, 2> weights{0.0, 2.0};
  std::piecewise_constant_distribution<double> distribution{
      boundaries.begin(), boundaries.end(), weights.begin()};

  const auto intervals = distribution.intervals();
  const auto densities = distribution.densities();
  EXPECT_EQ(intervals,
            (std::vector<double>{0.0, 1.0, 3.0}));
  ASSERT_EQ(densities.size(), 2U);
  EXPECT_DOUBLE_EQ(densities[0], 0.0);
  EXPECT_NEAR(densities[1], 0.5, 1e-15);

  std::mt19937 engine{47U};
  ExpectSamplesSatisfy(distribution, engine, 50, [](double value) {
    return value >= 1.0 && value < 3.0;
  });

  // densities() 返回归一化后的概率密度，不是构造权重；第二段长度为 2，所以总面积
  // 为 1 时密度是 0.5。
}

TEST(SamplingDistribution, PiecewiseLinearInterpolatesDensitiesAtKnots) {
  const std::array<double, 3> boundaries{0.0, 1.0, 2.0};
  const std::array<double, 3> weights{0.0, 1.0, 0.0};
  std::piecewise_linear_distribution<double> distribution{
      boundaries.begin(), boundaries.end(), weights.begin()};

  const auto intervals = distribution.intervals();
  const auto densities = distribution.densities();
  EXPECT_EQ(intervals,
            (std::vector<double>{0.0, 1.0, 2.0}));
  ASSERT_EQ(densities.size(), 3U);
  EXPECT_NEAR(densities[0], 0.0, 1e-15);
  EXPECT_NEAR(densities[1], 1.0, 1e-15);
  EXPECT_NEAR(densities[2], 0.0, 1e-15);

  std::mt19937 engine{53U};
  ExpectSamplesSatisfy(distribution, engine, 50, [](double value) {
    return value >= 0.0 && value < 2.0;
  });

  // piecewise_linear 在相邻结点密度间线性插值；权重数量与边界数量相同，而
  // piecewise_constant 的权重数量比边界少一。
}

TEST(DistributionState, ResetClearsCachedValuesWithoutChangingParameters) {
  std::normal_distribution<double> distribution{3.0, 2.0};
  std::mt19937 engine{59U};
  static_cast<void>(distribution(engine));

  distribution.reset();

  EXPECT_DOUBLE_EQ(distribution.mean(), 3.0);
  EXPECT_DOUBLE_EQ(distribution.stddev(), 2.0);

  // 某些分布会缓存一次变换产生的备用值。reset 清除这类内部缓存，但不重置参数，也不
  // 重置引擎；重放完整序列通常要同时重建或恢复两者状态。
}

TEST(DistributionState, StreamRoundTripPreservesCachedDistributionState) {
  std::normal_distribution<double> source{1.0, 0.5};
  std::mt19937 source_engine{61U};
  static_cast<void>(source(source_engine));

  std::ostringstream output;
  output << source;
  ASSERT_TRUE(output);

  std::normal_distribution<double> restored;
  std::istringstream input{output.str()};
  input >> restored;
  ASSERT_TRUE(input);

  std::mt19937 restored_engine = source_engine;
  EXPECT_DOUBLE_EQ(restored(restored_engine), source(source_engine));

  // 对可能缓存样本的分布，只保存参数不足以继续精确序列；流状态包含实现所需的缓存。
}

TEST(SamplingWorkflow, FixedSeedAllowsAStableStatisticalRegressionCheck) {
  std::mt19937 engine{67U};
  std::normal_distribution<double> standard_normal{0.0, 1.0};
  std::vector<double> samples(20'000);
  std::generate(samples.begin(), samples.end(), [&] {
    return standard_normal(engine);
  });

  const double sum = std::accumulate(samples.begin(), samples.end(), 0.0);
  const double mean = sum / static_cast<double>(samples.size());
  const double squared_sum = std::inner_product(
      samples.begin(), samples.end(), samples.begin(), 0.0);
  const double variance = squared_sum / static_cast<double>(samples.size()) -
                          mean * mean;

  EXPECT_NEAR(mean, 0.0, 0.03);
  EXPECT_NEAR(variance, 1.0, 0.05);

  // 固定 seed 消除偶发波动，宽容差只检查工作流是否严重偏离目标分布；它不是对标准库
  // 随机质量的完整统计认证。
}

static_assert(std::is_same_v<
              std::uniform_int_distribution<short>::result_type,
              short>);
static_assert(std::is_same_v<
              std::normal_distribution<float>::result_type,
              float>);

}  // namespace
