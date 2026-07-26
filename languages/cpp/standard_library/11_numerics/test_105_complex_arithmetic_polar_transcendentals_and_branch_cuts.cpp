// polyglot-covers:
// - cpp.stdlib.complex.construction-access-and-component-mutation
// - cpp.stdlib.complex.arithmetic-and-scalar-overloads
// - cpp.stdlib.complex.division-and-zero-precondition
// - cpp.stdlib.complex.abs-norm-arg-and-polar
// - cpp.stdlib.complex.conjugate-and-riemann-sphere-projection
// - cpp.stdlib.complex.exp-log-pow-and-sqrt
// - cpp.stdlib.complex.trigonometric-and-hyperbolic-functions
// - cpp.stdlib.complex.signed-zero-and-branch-cut-selection
// - cpp.stdlib.complex.imaginary-literals-and-result-types
// - cpp.stdlib.complex.formatted-stream-input-and-output
// - cpp.stdlib.complex.no-relational-ordering

#include <gtest/gtest.h>

#include <cmath>
#include <complex>
#include <limits>
#include <sstream>
#include <type_traits>

namespace {

constexpr double kTolerance = 1e-12;

void ExpectComplexNear(
    const std::complex<double>& actual,
    const std::complex<double>& expected,
    double tolerance = kTolerance) {
  EXPECT_NEAR(actual.real(), expected.real(), tolerance);
  EXPECT_NEAR(actual.imag(), expected.imag(), tolerance);
}

TEST(ComplexConstruction, DefaultAndScalarConstructionSetMissingPartsToZero) {
  const std::complex<double> default_value;
  const std::complex<double> scalar_value{3.5};
  const std::complex<double> full_value{3.5, -2.0};

  EXPECT_DOUBLE_EQ(default_value.real(), 0.0);
  EXPECT_DOUBLE_EQ(default_value.imag(), 0.0);
  EXPECT_DOUBLE_EQ(scalar_value.real(), 3.5);
  EXPECT_DOUBLE_EQ(scalar_value.imag(), 0.0);
  EXPECT_DOUBLE_EQ(full_value.real(), 3.5);
  EXPECT_DOUBLE_EQ(full_value.imag(), -2.0);
}

TEST(ComplexConstruction, RealAndImagSettersMutateComponentsIndependently) {
  std::complex<double> value{1.0, 2.0};

  value.real(4.0);
  EXPECT_EQ(value, std::complex<double>(4.0, 2.0));
  value.imag(-3.0);
  EXPECT_EQ(value, std::complex<double>(4.0, -3.0));

  // real()/imag() 的无参重载按值返回，不提供可绑定并长期持有的分量引用；修改应使用
  // 带参数的 setter 或对整个 complex 赋值。
}

TEST(ComplexArithmetic, AdditionSubtractionAndMultiplicationFollowAlgebra) {
  const std::complex<double> left{2.0, 3.0};
  const std::complex<double> right{4.0, -1.0};

  EXPECT_EQ(left + right, std::complex<double>(6.0, 2.0));
  EXPECT_EQ(left - right, std::complex<double>(-2.0, 4.0));
  EXPECT_EQ(left * right, std::complex<double>(11.0, 10.0));
  EXPECT_EQ(-left, std::complex<double>(-2.0, -3.0));

  // (a+bi)(c+di)=(ac-bd)+(ad+bc)i；不能把实部、虚部分别相乘。
}

TEST(ComplexArithmetic, ScalarOverloadsTreatTheScalarAsZeroImaginary) {
  const std::complex<double> value{2.0, 3.0};

  EXPECT_EQ(value + 4.0, std::complex<double>(6.0, 3.0));
  EXPECT_EQ(4.0 - value, std::complex<double>(2.0, -3.0));
  EXPECT_EQ(value * 2.0, std::complex<double>(4.0, 6.0));
  EXPECT_EQ(value / 2.0, std::complex<double>(1.0, 1.5));

  std::complex<double> accumulated{1.0, 1.0};
  accumulated += 2.0;
  accumulated *= std::complex<double>{0.0, 1.0};
  EXPECT_EQ(accumulated, std::complex<double>(-1.0, 3.0));
}

TEST(ComplexArithmetic, DivisionMultipliesBackForANonzeroDivisor) {
  const std::complex<double> numerator{7.0, 5.0};
  const std::complex<double> denominator{2.0, -1.0};
  const auto quotient = numerator / denominator;

  ExpectComplexNear(quotient, {1.8, 3.4});
  ExpectComplexNear(quotient * denominator, numerator);

  // 分母为 0+0i 时不应期待普通有限结果；浮点特化会遵循浮点异常/NaN/无穷语义，
  // 但算法通常应在领域层面先排除零除数。
}

TEST(ComplexGeometry, AbsNormAndArgAnswerDifferentGeometricQuestions) {
  const std::complex<double> value{3.0, 4.0};
  const double pi = std::acos(-1.0);

  EXPECT_DOUBLE_EQ(std::abs(value), 5.0);
  EXPECT_DOUBLE_EQ(std::norm(value), 25.0);
  EXPECT_NEAR(std::arg(value), std::atan2(4.0, 3.0), kTolerance);
  EXPECT_NEAR(std::arg(std::complex<double>{-1.0, 0.0}), pi, kTolerance);

  // abs 是模长，norm 是模长平方而不是“归一化后的 complex”；arg 使用 atan2 语义，
  // 返回以弧度表示的相位。
}

TEST(ComplexGeometry, PolarConstructsFromMagnitudeAndAngle) {
  const double pi = std::acos(-1.0);

  ExpectComplexNear(std::polar(2.0, pi / 2.0), {0.0, 2.0});
  ExpectComplexNear(std::polar(3.0), {3.0, 0.0});

  // polar 的模长参数要求非负且不是 NaN；用负“半径”试探实现会违反前置条件。
}

TEST(ComplexGeometry, ConjugateReflectsAcrossTheRealAxis) {
  const std::complex<double> value{3.0, 4.0};

  EXPECT_EQ(std::conj(value), std::complex<double>(3.0, -4.0));
  EXPECT_EQ(value * std::conj(value), std::complex<double>(25.0, 0.0));
}

TEST(ComplexGeometry, ProjectionMapsInfiniteValuesToTheRiemannSphereInfinity) {
  const double infinity = std::numeric_limits<double>::infinity();
  const auto projected = std::proj(std::complex<double>{infinity, -2.0});

  EXPECT_TRUE(std::isinf(projected.real()));
  EXPECT_DOUBLE_EQ(projected.imag(), -0.0);
  EXPECT_TRUE(std::signbit(projected.imag()));

  const std::complex<double> finite{2.0, -3.0};
  EXPECT_EQ(std::proj(finite), finite);

  // proj 把任一无穷分量映射到黎曼球面的同一个无穷点，同时用虚部的 signed zero 保留
  // 接近方向；有限值保持不变。
}

TEST(ComplexExponentials, ExpAndLogRoundTripAwayFromBranchCuts) {
  const std::complex<double> value{0.75, 0.5};

  ExpectComplexNear(std::log(std::exp(value)), value);
  ExpectComplexNear(std::exp(std::complex<double>{0.0, 1.0}),
                    {std::cos(1.0), std::sin(1.0)});

  // complex log 是多值对数的主值；跨过分支切线时 log(exp(z)) 的虚部可能相差 2π，
  // 所以 round-trip 只在选定主值区域内成立。
}

TEST(ComplexExponentials, PowSupportsComplexAndScalarCombinations) {
  const std::complex<double> imaginary_unit{0.0, 1.0};

  ExpectComplexNear(std::pow(imaginary_unit, 2), {-1.0, 0.0});
  ExpectComplexNear(std::pow(std::complex<double>{4.0, 0.0}, 0.5), {2.0, 0.0});
  ExpectComplexNear(std::pow(4.0, std::complex<double>{0.5, 0.0}), {2.0, 0.0});

  // complex 幂通常通过 exp(y*log(x)) 定义，继承主值和分支切线语义；不能把所有实数
  // pow 的直觉原样推广到复平面。
}

TEST(ComplexBranchCuts, SqrtUsesSignedZeroToChooseTheSideOfTheCut) {
  const auto above = std::sqrt(std::complex<double>{-4.0, 0.0});
  const auto below = std::sqrt(std::complex<double>{-4.0, -0.0});

  EXPECT_DOUBLE_EQ(above.real(), 0.0);
  EXPECT_DOUBLE_EQ(above.imag(), 2.0);
  EXPECT_DOUBLE_EQ(below.real(), 0.0);
  EXPECT_DOUBLE_EQ(below.imag(), -2.0);
  EXPECT_TRUE(std::signbit(below.imag()));

  // 负实轴是主平方根的分支切线；+0i 与 -0i 表示从切线两侧逼近，决定结果虚部符号。
}

TEST(ComplexTrigonometry, TrigonometricFunctionsAcceptComplexArguments) {
  const std::complex<double> value{0.4, -0.3};

  ExpectComplexNear(std::asin(std::sin(value)), value);
  ExpectComplexNear(std::atan(std::tan(value)), value);
  ExpectComplexNear(
      std::sin(value) * std::sin(value) + std::cos(value) * std::cos(value),
      {1.0, 0.0});

  // 逆函数同样只返回主值，round-trip 测试选择远离周期边界和分支切线的小参数。
}

TEST(ComplexHyperbolic, HyperbolicIdentitiesExtendToComplexArguments) {
  const std::complex<double> value{0.3, 0.2};

  ExpectComplexNear(std::asinh(std::sinh(value)), value);
  ExpectComplexNear(
      std::cosh(value) * std::cosh(value) - std::sinh(value) * std::sinh(value),
      {1.0, 0.0});
  ExpectComplexNear(std::tanh(value), std::sinh(value) / std::cosh(value));
}

TEST(ComplexValueOverloads, ArithmeticArgumentsArePromotedForValueOperations) {
  EXPECT_DOUBLE_EQ(std::real(4), 4.0);
  EXPECT_DOUBLE_EQ(std::imag(4), 0.0);
  EXPECT_DOUBLE_EQ(std::norm(4), 16.0);
  EXPECT_DOUBLE_EQ(std::arg(-4), std::acos(-1.0));
  EXPECT_EQ(std::conj(4), std::complex<double>(4.0, -0.0));

  static_assert(std::is_same_v<decltype(std::real(4)), double>);
  static_assert(std::is_same_v<decltype(std::conj(4)), std::complex<double>>);

  // 这些附加重载把整数提升到 double；不要从实参是 int 推断 norm 仍返回整数。
}

TEST(ComplexLiterals, SuffixSelectsTheComponentType) {
  using namespace std::complex_literals;

  constexpr auto double_imaginary = 2.0i;
  constexpr auto float_imaginary = 2.0if;
  constexpr auto long_double_imaginary = 2.0il;

  static_assert(std::is_same_v<decltype(double_imaginary),
                               const std::complex<double>>);
  static_assert(std::is_same_v<decltype(float_imaginary),
                               const std::complex<float>>);
  static_assert(std::is_same_v<decltype(long_double_imaginary),
                               const std::complex<long double>>);
  static_assert(double_imaginary.real() == 0.0);
  static_assert(double_imaginary.imag() == 2.0);

  EXPECT_EQ(3.0 + 2.0i, std::complex<double>(3.0, 2.0));

  // `i` 只在 std::complex_literals（也可经 std::literals）中可见，避免无意污染全局
  // 字面量后缀命名空间；if/il 分别选择 float/long double。
}

TEST(ComplexStreams, OutputUsesParenthesizedRealCommaImaginaryForm) {
  std::ostringstream output;
  output << std::complex<double>{3.0, -4.0};

  EXPECT_EQ(output.str(), "(3,-4)");
}

TEST(ComplexStreams, InputAcceptsPairSingleParenthesizedAndBareRealForms) {
  std::istringstream input{"(3,4) (5) 6"};
  std::complex<double> pair;
  std::complex<double> parenthesized_real;
  std::complex<double> bare_real;

  input >> pair >> parenthesized_real >> bare_real;

  ASSERT_TRUE(input);
  EXPECT_EQ(pair, std::complex<double>(3.0, 4.0));
  EXPECT_EQ(parenthesized_real, std::complex<double>(5.0, 0.0));
  EXPECT_EQ(bare_real, std::complex<double>(6.0, 0.0));
}

template <class T>
concept LessThanComparableComplex = requires(std::complex<T> left,
                                             std::complex<T> right) {
  left < right;
};

TEST(ComplexComparison, EqualityExistsButThereIsNoNaturalRelationalOrdering) {
  EXPECT_EQ(std::complex<double>(2.0, 3.0), std::complex<double>(2.0, 3.0));
  EXPECT_NE(std::complex<double>(2.0, 3.0), std::complex<double>(3.0, 2.0));
  static_assert(!LessThanComparableComplex<double>);

  // 复数没有与代数相容的全序，标准库只提供相等比较。若业务需要按模长或字典序排序，
  // 必须显式提供比较准则并处理相等模长、NaN 等情况。
}

constexpr std::complex<double> kCompileTimeComplex{2.0, -3.0};
static_assert(kCompileTimeComplex.real() == 2.0);
static_assert(kCompileTimeComplex.imag() == -3.0);

}  // namespace
