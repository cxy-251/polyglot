// polyglot-covers:
// - cpp.stdlib.cmath.fpclassify-finite-infinite-nan-normal-subnormal
// - cpp.stdlib.cmath.signbit-and-signed-zero
// - cpp.stdlib.cmath.nan-safe-comparison-functions
// - cpp.stdlib.cmath.fmod-remainder-remquo-and-modf
// - cpp.stdlib.cmath.frexp-ldexp-scalbn-ilogb-and-logb
// - cpp.stdlib.cmath.nextafter-nexttoward-and-copysign
// - cpp.stdlib.cmath.fdim-fmin-fmax-and-nan-handling
// - cpp.stdlib.cmath.fma-single-rounding
// - cpp.stdlib.cmath.power-root-exponential-and-logarithmic-families
// - cpp.stdlib.cmath.trigonometric-and-hyperbolic-families
// - cpp.stdlib.cmath.hypot-overflow-resistant-norm
// - cpp.stdlib.cmath.lerp-interpolation-and-extrapolation
// - cpp.stdlib.cmath.gamma-and-error-functions

#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <type_traits>

namespace {

TEST(FloatingClassification, ItDistinguishesFiniteInfiniteNanAndNormalValues) {
  const double infinity = std::numeric_limits<double>::infinity();
  const double quiet_nan = std::numeric_limits<double>::quiet_NaN();

  EXPECT_TRUE(std::isfinite(1.0));
  EXPECT_FALSE(std::isfinite(infinity));
  EXPECT_FALSE(std::isfinite(quiet_nan));
  EXPECT_TRUE(std::isinf(infinity));
  EXPECT_TRUE(std::isnan(quiet_nan));
  EXPECT_TRUE(std::isnormal(1.0));
  EXPECT_FALSE(std::isnormal(0.0));

  EXPECT_EQ(std::fpclassify(0.0), FP_ZERO);
  EXPECT_EQ(std::fpclassify(1.0), FP_NORMAL);
  EXPECT_EQ(std::fpclassify(infinity), FP_INFINITE);
  EXPECT_EQ(std::fpclassify(quiet_nan), FP_NAN);

  // NaN 既不是有限数也不是无穷；normal 又排除了零和 subnormal。不要用单个谓词的
  // false 分支推断唯一类别，需要完整分类时使用 fpclassify。
}

TEST(FloatingClassification, DenormMinIsSubnormalWhenTheTypeSupportsIt) {
  if constexpr (std::numeric_limits<double>::has_denorm != std::denorm_absent) {
    const double smallest_subnormal = std::numeric_limits<double>::denorm_min();
    EXPECT_EQ(std::fpclassify(smallest_subnormal), FP_SUBNORMAL);
    EXPECT_TRUE(std::isfinite(smallest_subnormal));
    EXPECT_FALSE(std::isnormal(smallest_subnormal));
  } else {
    GTEST_SKIP() << "该实现没有 double subnormal";
  }
}

TEST(FloatingClassification, SignbitObservesNegativeZeroAndNanSignBits) {
  const double negative_zero = -0.0;
  const double positive_zero = 0.0;

  EXPECT_EQ(negative_zero, positive_zero);
  EXPECT_TRUE(std::signbit(negative_zero));
  EXPECT_FALSE(std::signbit(positive_zero));
  EXPECT_TRUE(std::signbit(std::copysign(
      std::numeric_limits<double>::quiet_NaN(), -1.0)));

  // 普通比较认为 +0 和 -0 相等，signbit 才读取符号位。NaN 也可以携带符号，但符号不
  // 改变其 unordered 比较语义。
}

TEST(FloatingComparison, NamedPredicatesHandleUnorderedNanWithoutAdHocLogic) {
  const double nan = std::numeric_limits<double>::quiet_NaN();

  EXPECT_TRUE(std::isgreater(3.0, 2.0));
  EXPECT_TRUE(std::isgreaterequal(3.0, 3.0));
  EXPECT_TRUE(std::isless(2.0, 3.0));
  EXPECT_TRUE(std::islessequal(3.0, 3.0));
  EXPECT_TRUE(std::islessgreater(2.0, 3.0));
  EXPECT_FALSE(std::islessgreater(3.0, 3.0));
  EXPECT_TRUE(std::isunordered(nan, 1.0));
  EXPECT_FALSE(std::isgreater(nan, 1.0));

  // islessgreater 表示“有序且不相等”，不是 `a != b` 的同义词：NaN != x 为 true，
  // 但 islessgreater(NaN, x) 为 false。
}

TEST(FloatingRemainders, FmodAndRemainderChooseDifferentIntegerQuotients) {
  EXPECT_DOUBLE_EQ(std::fmod(7.0, 4.0), 3.0);
  EXPECT_DOUBLE_EQ(std::remainder(7.0, 4.0), -1.0);
  EXPECT_DOUBLE_EQ(std::fmod(-7.0, 4.0), -3.0);
  EXPECT_DOUBLE_EQ(std::remainder(-7.0, 4.0), 1.0);

  // fmod 使用向零截断的商：7 - trunc(7/4)*4 == 3。remainder 使用最接近整数的商，
  // 恰好中点时取偶数，因此 7 - 2*4 == -1。
}

TEST(FloatingRemainders, RemquoAlsoReturnsLowQuotientBits) {
  int quotient_bits = 0;
  const double remainder = std::remquo(7.0, 4.0, &quotient_bits);

  EXPECT_DOUBLE_EQ(remainder, -1.0);
  EXPECT_EQ(quotient_bits, 2);

  // remquo 的浮点结果与 remainder 相同，并写出带符号商的若干低位；标准只保证至少
  // 三位，不能把输出当作完整大商。
}

TEST(FloatingDecomposition, ModfSplitsFractionAndIntegralPartsTowardZero) {
  double integral_part = 0.0;
  const double fractional_part = std::modf(-3.25, &integral_part);

  EXPECT_DOUBLE_EQ(integral_part, -3.0);
  EXPECT_DOUBLE_EQ(fractional_part, -0.25);

  const double negative_zero_fraction = std::modf(-2.0, &integral_part);
  EXPECT_TRUE(std::signbit(negative_zero_fraction));

  // 两部分都保留输入符号；整数输入的“小数部分”可能是 -0.0，不能只靠相等比较观察。
}

TEST(FloatingDecomposition, FrexpAndLdexpRoundTripBinaryExponentForm) {
  int exponent = 0;
  const double significand = std::frexp(12.0, &exponent);

  EXPECT_DOUBLE_EQ(significand, 0.75);
  EXPECT_EQ(exponent, 4);
  EXPECT_DOUBLE_EQ(std::ldexp(significand, exponent), 12.0);
  EXPECT_DOUBLE_EQ(std::scalbn(1.5, 3), 12.0);

  // frexp 产生 x = significand * 2^exponent，非零 significand 的绝对值位于
  // [0.5, 1)。ldexp 按二进制指数缩放，scalbn 按 FLT_RADIX 的幂缩放。
}

TEST(FloatingDecomposition, IlogbAndLogbExposeTheUnbiasedRadixExponent) {
  EXPECT_EQ(std::ilogb(8.0), 3);
  EXPECT_DOUBLE_EQ(std::logb(8.0), 3.0);
  EXPECT_EQ(std::ilogb(0.75), -1);

  // ilogb 返回 int，logb 返回浮点值。零、无穷和 NaN 各有特殊返回及错误语义，这里
  // 不把 FP_ILOGB0 等实现宏误当普通有限指数。
}

TEST(FloatingNeighbors, NextafterMovesExactlyOneRepresentableStep) {
  const double upward = std::nextafter(1.0, 2.0);
  const double downward = std::nextafter(1.0, 0.0);

  EXPECT_GT(upward, 1.0);
  EXPECT_LT(downward, 1.0);
  EXPECT_EQ(std::nextafter(upward, 0.0), 1.0);
  EXPECT_EQ(std::nexttoward(1.0, 2.0L), upward);

  // 加 epsilon 不是通用的“下一个浮点数”：间距随指数变化。nextafter 的方向参数与
  // 返回类型相同，nexttoward 则用 long double 表达方向。
}

TEST(FloatingNeighbors, CopysignTransfersAHiddenZeroSign) {
  const double negative = std::copysign(3.0, -0.0);
  const double positive = std::copysign(-3.0, 0.0);

  EXPECT_DOUBLE_EQ(negative, -3.0);
  EXPECT_DOUBLE_EQ(positive, 3.0);
  EXPECT_TRUE(std::signbit(negative));
  EXPECT_FALSE(std::signbit(positive));
}

TEST(FloatingMinMax, NanAndPositiveDifferenceHaveSpecifiedHandling) {
  const double nan = std::numeric_limits<double>::quiet_NaN();

  EXPECT_DOUBLE_EQ(std::fmax(nan, 4.0), 4.0);
  EXPECT_DOUBLE_EQ(std::fmin(4.0, nan), 4.0);
  EXPECT_TRUE(std::isnan(std::fmax(nan, nan)));
  EXPECT_DOUBLE_EQ(std::fdim(7.0, 4.0), 3.0);
  EXPECT_DOUBLE_EQ(std::fdim(4.0, 7.0), 0.0);

  // fmax/fmin 在恰有一个 NaN 时返回数值实参，和普通比较加三元表达式对 NaN 的结果
  // 未必一致。fdim 计算正差 max(x-y, 0)，任一参数为 NaN 时才返回 NaN。
}

TEST(FusedMultiplyAdd, ItRoundsTheWholeExpressionOnlyOnce) {
  constexpr double delta = 0x1p-27;
  const double left = 1.0 + delta;
  const double right = 1.0 - delta;

  const double separately_rounded = left * right - 1.0;
  const double fused = std::fma(left, right, -1.0);

  EXPECT_DOUBLE_EQ(separately_rounded, 0.0);
  EXPECT_DOUBLE_EQ(fused, -0x1p-54);

  // 精确乘积为 1 - 2^-54。普通乘法先舍入到 1，再减得到 0；fma 把乘加作为整体只
  // 舍入一次，保留了 -2^-54。是否由硬件指令实现不改变这个语义保证。
}

TEST(ElementaryMath, PowersRootsExponentialsAndLogarithmsComposeCommonWorkflows) {
  EXPECT_DOUBLE_EQ(std::sqrt(81.0), 9.0);
  EXPECT_DOUBLE_EQ(std::cbrt(-8.0), -2.0);
  EXPECT_DOUBLE_EQ(std::pow(2.0, 10.0), 1024.0);
  EXPECT_DOUBLE_EQ(std::exp2(5.0), 32.0);
  EXPECT_DOUBLE_EQ(std::log2(32.0), 5.0);
  EXPECT_NEAR(std::log(std::exp(1.25)), 1.25, 1e-12);
  EXPECT_NEAR(std::log10(1000.0), 3.0, 1e-12);
}

TEST(ElementaryMath, Expm1AndLog1pPreserveInformationNearZero) {
  constexpr double tiny = 1e-16;

  EXPECT_DOUBLE_EQ(std::exp(tiny), 1.0);
  EXPECT_DOUBLE_EQ(std::exp(tiny) - 1.0, 0.0);
  EXPECT_GT(std::expm1(tiny), 0.0);
  EXPECT_NEAR(std::log1p(tiny), tiny, 1e-30);

  // exp(x)-1 和 log(1+x) 在 x 接近零时会因相减或相加丢失有效位；expm1/log1p
  // 专门为该区域保留精度。
}

TEST(ElementaryMath, TrigonometricFunctionsUseRadiansAndHaveInversePairs) {
  const double pi = std::acos(-1.0);

  EXPECT_NEAR(std::sin(pi / 2.0), 1.0, 1e-12);
  EXPECT_NEAR(std::cos(pi), -1.0, 1e-12);
  EXPECT_NEAR(std::tan(pi / 4.0), 1.0, 1e-12);
  EXPECT_NEAR(std::asin(0.5), pi / 6.0, 1e-12);
  EXPECT_NEAR(std::acos(0.5), pi / 3.0, 1e-12);
  EXPECT_NEAR(std::atan2(1.0, -1.0), 3.0 * pi / 4.0, 1e-12);

  // atan2(y, x) 同时使用两坐标选择象限；写成 atan(y/x) 会丢失象限，并在 x==0 时
  // 制造额外问题。
}

TEST(ElementaryMath, HyperbolicFunctionsAndTheirInversesRoundTrip) {
  EXPECT_DOUBLE_EQ(std::sinh(0.0), 0.0);
  EXPECT_DOUBLE_EQ(std::cosh(0.0), 1.0);
  EXPECT_DOUBLE_EQ(std::tanh(0.0), 0.0);
  EXPECT_NEAR(std::asinh(std::sinh(0.75)), 0.75, 1e-12);
  EXPECT_NEAR(std::acosh(std::cosh(0.75)), 0.75, 1e-12);
  EXPECT_NEAR(std::atanh(std::tanh(0.5)), 0.5, 1e-12);
}

TEST(ElementaryMath, HypotAvoidsIntermediateOverflowAndUnderflow) {
  const double half_maximum = std::numeric_limits<double>::max() / 2.0;
  const double length = std::hypot(half_maximum, half_maximum);

  EXPECT_TRUE(std::isfinite(length));
  EXPECT_GT(length, half_maximum);
  EXPECT_NEAR(std::hypot(3.0, 4.0, 12.0), 13.0, 1e-12);

  // 直接 sqrt(x*x+y*y) 的平方中间值可能溢出；hypot 的结果只要可表示，就应避免不当
  // 的中间溢出或下溢。C++17 起还提供三参数重载。
}

TEST(ElementaryMath, LerpHandlesEndpointsInterpolationAndExtrapolation) {
  EXPECT_DOUBLE_EQ(std::lerp(10.0, 20.0, 0.0), 10.0);
  EXPECT_DOUBLE_EQ(std::lerp(10.0, 20.0, 1.0), 20.0);
  EXPECT_DOUBLE_EQ(std::lerp(10.0, 20.0, 0.25), 12.5);
  EXPECT_DOUBLE_EQ(std::lerp(10.0, 20.0, 1.5), 25.0);

  // t 不限于 [0,1]，区间外是外插。lerp 还规定了单调性和有限端点下的精确端点语义，
  // 比直接写 a+t*(b-a) 更能避免某些中间溢出和舍入反常。
}

TEST(ElementaryMath, GammaAndErrorFunctionsCoverCommonProbabilityBuildingBlocks) {
  EXPECT_NEAR(std::tgamma(5.0), 24.0, 1e-12);
  EXPECT_NEAR(std::lgamma(5.0), std::log(24.0), 1e-12);
  EXPECT_DOUBLE_EQ(std::erf(0.0), 0.0);
  EXPECT_DOUBLE_EQ(std::erfc(0.0), 1.0);
  EXPECT_NEAR(std::erf(1.0) + std::erfc(1.0), 1.0, 1e-15);

  // tgamma 返回 Gamma(x)，lgamma 返回 |Gamma(x)| 的自然对数；大参数时后者更不易
  // 直接溢出。erfc 在大正数区域通常也比 1-erf(x) 保留更多尾部精度。
}

static_assert(std::is_same_v<decltype(std::sqrt(4)), double>);
static_assert(std::is_same_v<decltype(std::abs(-4.0F)), float>);

}  // namespace
