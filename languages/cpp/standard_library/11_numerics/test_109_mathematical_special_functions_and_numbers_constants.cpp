// polyglot-covers:
// - cpp.stdlib.cmath.special-functions-feature-test-and-domain-preconditions
// - cpp.stdlib.cmath.laguerre-associated-laguerre-hermite-polynomials
// - cpp.stdlib.cmath.legendre-and-associated-legendre-functions
// - cpp.stdlib.cmath.beta-and-gamma-relation
// - cpp.stdlib.cmath.complete-elliptic-integrals-first-second-third-kind
// - cpp.stdlib.cmath.incomplete-elliptic-integrals-first-second-third-kind
// - cpp.stdlib.cmath.cylindrical-bessel-i-j-k-and-neumann
// - cpp.stdlib.cmath.exponential-integral-and-riemann-zeta
// - cpp.stdlib.cmath.spherical-bessel-legendre-and-neumann
// - cpp.stdlib.numbers.constants-complete-cpp20-set
// - cpp.stdlib.numbers.variable-template-type-and-compile-time-precision

#include <gtest/gtest.h>

#include <cmath>
#include <numbers>
#include <type_traits>

namespace {

constexpr double kTolerance = 1e-11;

#if defined(__cpp_lib_math_special_functions) && \
    __cpp_lib_math_special_functions >= 201603L

TEST(MathSpecialFunctions, FeatureTestMacroAdvertisesTheCxx17Facility) {
  static_assert(__cpp_lib_math_special_functions >= 201603L);

  // 特殊函数在 C++17 进入标准库。它们不是普通 <cmath> 基础函数的必然扩展；旧工具链
  // 应通过特性宏检测，而不是等到链接阶段才发现缺失。
}

TEST(OrthogonalPolynomials, LaguerreAndAssociatedLaguerreUseDegreeAndOrder) {
  constexpr double x = 0.25;

  EXPECT_NEAR(std::laguerre(0U, x), 1.0, kTolerance);
  EXPECT_NEAR(std::laguerre(1U, x), 1.0 - x, kTolerance);
  EXPECT_NEAR(std::laguerre(2U, x), 1.0 - 2.0 * x + x * x / 2.0,
              kTolerance);
  EXPECT_NEAR(std::assoc_laguerre(2U, 0U, x), std::laguerre(2U, x),
              kTolerance);
  EXPECT_NEAR(std::assoc_laguerre(0U, 3U, x), 1.0, kTolerance);

  // 参数顺序是 degree n、order m、x。标准只要求 n、m 在实现支持的范围内；极大阶数
  // 可能报告 domain error，不应拿越界阶数探索实现内部。
}

TEST(OrthogonalPolynomials, HermiteMatchesItsFirstClosedForms) {
  constexpr double x = 0.75;

  EXPECT_NEAR(std::hermite(0U, x), 1.0, kTolerance);
  EXPECT_NEAR(std::hermite(1U, x), 2.0 * x, kTolerance);
  EXPECT_NEAR(std::hermite(2U, x), 4.0 * x * x - 2.0, kTolerance);
}

TEST(OrthogonalPolynomials, LegendreAndAssociatedOrderZeroAgree) {
  constexpr double x = 0.4;

  EXPECT_NEAR(std::legendre(0U, x), 1.0, kTolerance);
  EXPECT_NEAR(std::legendre(1U, x), x, kTolerance);
  EXPECT_NEAR(std::legendre(2U, x), (3.0 * x * x - 1.0) / 2.0,
              kTolerance);
  EXPECT_NEAR(std::assoc_legendre(2U, 0U, x), std::legendre(2U, x),
              kTolerance);

  // assoc_legendre 的 order 要满足 m<=n，实参 x 的有效区间是 [-1,1]。不同领域对
  // Condon–Shortley 相位的约定可能不同，使用公式前要核对 C++ 标准采用的定义。
}

TEST(BetaFunction, ItAgreesWithTheGammaIdentityAtSimpleArguments) {
  EXPECT_NEAR(std::beta(1.0, 4.0), 0.25, kTolerance);
  EXPECT_NEAR(std::beta(2.0, 3.0), 1.0 / 12.0, kTolerance);

  const double via_gamma =
      std::tgamma(2.0) * std::tgamma(3.0) / std::tgamma(5.0);
  EXPECT_NEAR(std::beta(2.0, 3.0), via_gamma, kTolerance);

  // 大参数时直接拼接 Gamma 可能先溢出；beta 的专用实现可采用对数或缩放算法。
}

TEST(CompleteEllipticIntegrals, ZeroParametersReduceToHalfPi) {
  const double half_pi = std::numbers::pi / 2.0;

  EXPECT_NEAR(std::comp_ellint_1(0.0), half_pi, kTolerance);
  EXPECT_NEAR(std::comp_ellint_2(0.0), half_pi, kTolerance);
  EXPECT_NEAR(std::comp_ellint_3(0.0, 0.0), half_pi, kTolerance);

  // 第三类参数顺序是 k、nu；不同数学资料常用 m=k² 或交换符号约定，移植公式时必须
  // 明确参数化方式。
}

TEST(IncompleteEllipticIntegrals, ZeroParametersReduceToTheAmplitude) {
  constexpr double amplitude = 0.7;

  EXPECT_NEAR(std::ellint_1(0.0, amplitude), amplitude, kTolerance);
  EXPECT_NEAR(std::ellint_2(0.0, amplitude), amplitude, kTolerance);
  EXPECT_NEAR(std::ellint_3(0.0, 0.0, amplitude), amplitude, kTolerance);

  // incomplete 版本额外接收振幅 phi；第三类顺序为 k、nu、phi。
}

TEST(CylindricalFunctions, BesselFamiliesCoverRegularAndIrregularSolutions) {
  EXPECT_NEAR(std::cyl_bessel_i(0.0, 0.0), 1.0, kTolerance);
  EXPECT_NEAR(std::cyl_bessel_j(0.0, 0.0), 1.0, kTolerance);
  EXPECT_GT(std::cyl_bessel_k(0.0, 1.0), 0.0);
  EXPECT_TRUE(std::isfinite(std::cyl_neumann(0.0, 1.0)));

  // I/J 在原点的零阶值有限；K 和 Neumann 在原点奇异，所以示例使用正 x。第一个参数
  // 是实数阶数 nu，不是只能传整数的模板阶数。
}

TEST(AnalyticSpecialFunctions, ExpintAndZetaMatchKnownReferenceValues) {
  EXPECT_NEAR(std::expint(1.0), 1.8951178163559368, kTolerance);
  EXPECT_NEAR(std::riemann_zeta(2.0),
              std::numbers::pi * std::numbers::pi / 6.0,
              kTolerance);

  // zeta 在 s=1 有极点；expint 在零附近也有奇异行为。非法或奇异参数应按错误策略
  // 处理，不应强求普通有限返回值。
}

TEST(SphericalFunctions, OrderZeroHasSimpleTrigonometricForms) {
  constexpr double x = 1.0;

  EXPECT_NEAR(std::sph_bessel(0U, x), std::sin(x) / x, kTolerance);
  EXPECT_NEAR(std::sph_neumann(0U, x), -std::cos(x) / x, kTolerance);
  EXPECT_NEAR(std::sph_legendre(0U, 0U, 0.8),
              1.0 / std::sqrt(4.0 * std::numbers::pi),
              kTolerance);

  // sph_legendre 的第三参数是极角 theta，不是 cos(theta)；这与普通 legendre 接收 x
  // 的接口尤其容易混淆。
}

TEST(MathSpecialFunctions, FloatAndLongDoubleOverloadsPreserveACommonType) {
  static_assert(std::is_same_v<decltype(std::beta(1.0F, 2.0F)), float>);
  static_assert(
      std::is_same_v<decltype(std::riemann_zeta(2.0L)), long double>);
  static_assert(std::is_same_v<decltype(std::beta(1, 2)), double>);

  EXPECT_NEAR(std::beta(1.0F, 2.0F), 0.5F, 1e-6F);

  // 同一浮点类型保持该类型；整数附加重载提升到 double。混合类型遵循公共浮点类型，
  // 不要仅凭函数名假定全部返回 double。
}

#else

TEST(MathSpecialFunctions, ToolchainGapIsExplicitlyRecorded) {
  GTEST_SKIP()
      << "锁定工具链未定义 __cpp_lib_math_special_functions >= 201603L；"
      << "覆盖已保留，升级 libstdc++ 后启用全部特殊函数案例";
}

#endif

TEST(NumbersConstants, Cxx20ProvidesTheCompleteNamedConstantSet) {
  EXPECT_NEAR(std::numbers::e, std::exp(1.0), 1e-15);
  EXPECT_NEAR(std::numbers::log2e, 1.0 / std::log(2.0), 1e-15);
  EXPECT_NEAR(std::numbers::log10e, 1.0 / std::log(10.0), 1e-15);
  EXPECT_NEAR(std::numbers::pi, std::acos(-1.0), 1e-15);
  EXPECT_NEAR(std::numbers::inv_pi * std::numbers::pi, 1.0, 1e-15);
  EXPECT_NEAR(std::numbers::inv_sqrtpi * std::sqrt(std::numbers::pi),
              1.0, 1e-15);
  EXPECT_NEAR(std::numbers::ln2, std::log(2.0), 1e-15);
  EXPECT_NEAR(std::numbers::ln10, std::log(10.0), 1e-15);
  EXPECT_NEAR(std::numbers::sqrt2 * std::numbers::sqrt2, 2.0, 1e-15);
  EXPECT_NEAR(std::numbers::sqrt3 * std::numbers::sqrt3, 3.0, 1e-15);
  EXPECT_NEAR(std::numbers::inv_sqrt3 * std::numbers::sqrt3, 1.0, 1e-15);
  EXPECT_NEAR(std::numbers::egamma, 0.5772156649015329, 1e-15);
  EXPECT_NEAR(std::numbers::phi,
              (1.0 + std::sqrt(5.0)) / 2.0,
              1e-15);

  // 这些名字位于 std::numbers，避免依赖非标准 M_PI 宏。inv_sqrtpi 是 1/sqrt(pi)，
  // egamma 是欧拉–马歇罗尼常数，phi 是黄金比例。
}

TEST(NumbersConstants, VariableTemplatesSelectFloatDoubleOrLongDoublePrecision) {
  static_assert(std::is_same_v<decltype(std::numbers::pi_v<float>),
                               const float>);
  static_assert(std::is_same_v<decltype(std::numbers::pi_v<double>),
                               const double>);
  static_assert(std::is_same_v<decltype(std::numbers::pi_v<long double>),
                               const long double>);
  static_assert(std::numbers::pi == std::numbers::pi_v<double>);
  static_assert(std::numbers::sqrt2_v<double> > 1.4);

  EXPECT_FLOAT_EQ(std::numbers::pi_v<float>,
                  static_cast<float>(std::numbers::pi));
  EXPECT_NEAR(std::numbers::pi_v<long double>,
              std::acos(-1.0L),
              1e-18L);

  // 无后缀名字是 `_v<double>` 的别名。需要 long double 精度时必须显式写 `_v<long
  // double>`；先取 double 常量再转换无法补回已舍入的位。模板参数要求浮点类型，
  // `pi_v<int>` 是程序错误而不是得到截断的 3。
}

constexpr long double kCircleIdentity =
    2.0L * std::numbers::pi_v<long double>;
static_assert(kCircleIdentity > 6.28L && kCircleIdentity < 6.29L);

}  // namespace
