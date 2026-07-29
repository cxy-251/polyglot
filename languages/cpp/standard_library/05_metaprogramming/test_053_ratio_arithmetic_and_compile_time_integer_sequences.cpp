// polyglot-covers:
// - cpp.stdlib.meta.ratio-normalization
// - cpp.stdlib.meta.ratio-arithmetic-and-comparison
// - cpp.stdlib.meta.ratio-si-prefixes
// - cpp.stdlib.meta.ratio-conversion-workflow
// - cpp.stdlib.meta.integer-sequence-interface
// - cpp.stdlib.meta.make-integer-and-index-sequence
// - cpp.stdlib.meta.index-sequence-for
// - cpp.stdlib.meta.integer-sequence-pack-expansion

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <ratio>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

namespace {

template <typename From, typename To>
constexpr double convert_scale(double value) {
  using Factor = std::ratio_divide<From, To>;
  return value * static_cast<double>(Factor::num) /
         static_cast<double>(Factor::den);
}

template <int... Values>
constexpr auto sequence_values(std::integer_sequence<int, Values...>) {
  return std::array<int, sizeof...(Values)>{Values...};
}

template <typename Tuple, std::size_t... Indexes>
auto select_tuple(Tuple&& tuple, std::index_sequence<Indexes...>) {
  return std::tuple{
      std::get<Indexes>(std::forward<Tuple>(tuple))...,
  };
}

TEST(Ratio, NormalizesTheSignAndGreatestCommonDivisor) {
  using Half = std::ratio<2, 4>;
  using Negative = std::ratio<6, -8>;
  using BothNegative = std::ratio<-10, -15>;

  static_assert(Half::num == 1);
  static_assert(Half::den == 2);
  static_assert(Negative::num == -3);
  static_assert(Negative::den == 4);
  static_assert(BothNegative::num == 2);
  static_assert(BothNegative::den == 3);

  // ratio 总把分母规范为正数，并用最大公约数约分，所以等价写法有统一的
  // num/den。分母为 0 不是运行期异常，而是模板实例化时的不合法程序。
}

TEST(Ratio, ArithmeticProducesANewCanonicalRatioType) {
  using OneThird = std::ratio<1, 3>;
  using OneSixth = std::ratio<1, 6>;
  using Sum = std::ratio_add<OneThird, OneSixth>;
  using Difference = std::ratio_subtract<OneThird, OneSixth>;
  using Product = std::ratio_multiply<std::ratio<2, 3>, std::ratio<9, 4>>;
  using Quotient = std::ratio_divide<std::ratio<3, 5>, std::ratio<9, 10>>;

  static_assert(std::ratio_equal_v<Sum, std::ratio<1, 2>>);
  static_assert(std::ratio_equal_v<Difference, std::ratio<1, 6>>);
  static_assert(std::ratio_equal_v<Product, std::ratio<3, 2>>);
  static_assert(std::ratio_equal_v<Quotient, std::ratio<2, 3>>);
  static_assert(std::ratio_less_v<OneSixth, OneThird>);
  static_assert(std::ratio_greater_equal_v<Sum, OneThird>);

  // ratio_add 等产生新类型，不执行运行期算术。实现会尽量在计算中约分，
  // 但若最终分子或分母无法由 intmax_t 表示，程序仍在编译期不合法。
}

TEST(Ratio, StandardPrefixesAreExactTypesRatherThanFloatingPointConstants) {
  static_assert(std::ratio_equal_v<std::kilo, std::ratio<1'000, 1>>);
  static_assert(std::ratio_equal_v<std::milli, std::ratio<1, 1'000>>);
  static_assert(std::ratio_equal_v<std::micro, std::ratio<1, 1'000'000>>);

  EXPECT_DOUBLE_EQ(
      (convert_scale<std::milli, std::ratio<1>>(1'500.0)),
      1.5);
  EXPECT_DOUBLE_EQ(
      (convert_scale<std::kilo, std::ratio<1>>(2.5)),
      2'500.0);

  // SI prefix 本身是 ratio type，换算因子在编译期保持精确分数，到真正处理
  // double 数值时才转为浮点。chrono::duration 的 Period 就使用这套机制。
}

TEST(IntegerSequence, CarriesAnIntegerPackAndItsValueType) {
  using Sequence = std::integer_sequence<int, 2, 3, 5, 7>;

  static_assert(std::is_same_v<Sequence::value_type, int>);
  static_assert(Sequence::size() == 4);
  constexpr auto values = sequence_values(Sequence{});
  static_assert(values == std::array<int, 4>{2, 3, 5, 7});
  EXPECT_EQ(values[2], 5);

  // integer_sequence 不存储运行期数组；将它传给函数模板后，Values...
  // 会被推导为非类型参数 pack，才能用 pack expansion 一次生成数组或调用。
}

TEST(IntegerSequence, FactoryAliasesGenerateZeroBasedHalfOpenSequences) {
  using Integers = std::make_integer_sequence<int, 5>;
  using Indexes = std::make_index_sequence<4>;
  using Empty = std::make_index_sequence<0>;

  static_assert(
      std::is_same_v<Integers, std::integer_sequence<int, 0, 1, 2, 3, 4>>);
  static_assert(std::is_same_v<Indexes, std::index_sequence<0, 1, 2, 3>>);
  static_assert(Empty::size() == 0);

  // make_integer_sequence<T, N> 生成 [0, N)，N 必须非负且能由 T 表示。
  // index_sequence 只是 value_type 固定为 size_t 的常用别名；N=0 产生空 pack。
}

TEST(IndexSequence, ExpandsSelectedTuplePositionsInAChosenOrder) {
  auto source = std::tuple{11, std::string{"middle"}, 2.5};
  auto selected = select_tuple(source, std::index_sequence<2, 0>{});

  static_assert(std::is_same_v<decltype(selected), std::tuple<double, int>>);
  EXPECT_DOUBLE_EQ(std::get<0>(selected), 2.5);
  EXPECT_EQ(std::get<1>(selected), 11);

  using ForArguments = std::index_sequence_for<int, std::string, double>;
  static_assert(std::is_same_v<ForArguments, std::index_sequence<0, 1, 2>>);

  // index_sequence 只提供索引 pack，次序和重复由使用者决定；它不会自动边界检查。
  // index_sequence_for<T...> 只按类型数量生成 0..N-1，不会读取或变换这些类型。
}

}  // namespace
