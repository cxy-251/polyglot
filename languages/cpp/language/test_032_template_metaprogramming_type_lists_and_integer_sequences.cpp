// polyglot-covers:
// - cpp.language.integral-constant-metafunction
// - cpp.language.template-metaprogramming-recursion
// - cpp.language.type-list
// - cpp.language.metafunction-lazy-selection
// - cpp.language.integer-sequence-pack-expansion
// - cpp.language.dependent-false-static-assert

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

namespace {

template <std::size_t Number>
struct TemplateFactorial
    : std::integral_constant<std::size_t, Number * TemplateFactorial<Number - 1>::value> {};

template <>
struct TemplateFactorial<0> : std::integral_constant<std::size_t, 1> {};

constexpr std::size_t constexpr_factorial(std::size_t number) {
  return number == 0 ? 1 : number * constexpr_factorial(number - 1);
}

template <typename... Values>
struct TypeList {};

template <typename List>
struct ListSize;

template <typename... Values>
struct ListSize<TypeList<Values...>> : std::integral_constant<std::size_t, sizeof...(Values)> {};

template <typename List>
struct Front;

template <typename First, typename... Rest>
struct Front<TypeList<First, Rest...>> {
  using type = First;
};

template <typename List, template <typename> typename Transform>
struct TransformList;

template <typename... Values, template <typename> typename Transform>
struct TransformList<TypeList<Values...>, Transform> {
  using type = TypeList<typename Transform<Values>::type...>;
};

template <typename... Conditions>
struct LazyAll;

template <>
struct LazyAll<> : std::true_type {};

template <typename First, typename... Rest>
struct LazyAll<First, Rest...>
    : std::conditional_t<First::value, LazyAll<Rest...>, std::false_type> {};

struct HasNoValueMember {};

template <std::size_t... Indexes>
constexpr auto squares(std::index_sequence<Indexes...>) {
  return std::array<std::size_t, sizeof...(Indexes)>{(Indexes * Indexes)...};
}

template <typename>
inline constexpr bool dependent_false_v = false;

template <typename Value>
std::string category_name() {
  if constexpr (std::is_integral_v<Value>) {
    return "integral";
  } else if constexpr (std::is_floating_point_v<Value>) {
    return "floating point";
  } else {
    // 不能直接写 static_assert(false)：在旧规则下它可能在模板定义时立刻失败。
    static_assert(dependent_false_v<Value>, "category_name does not support this type");
  }
}

TEST(Metafunctions, IntegralConstantCarriesAValueInAType) {
  static_assert(TemplateFactorial<5>::value == 120);
  static_assert(std::is_base_of_v<std::integral_constant<std::size_t, 120>,
                                  TemplateFactorial<5>>);
  static_assert(constexpr_factorial(5) == 120);
  SUCCEED();

  // 传统 TMP 用 specialization 提供递归基例，并把结果放进类型。能用普通 constexpr
  // 函数表达的数值算法通常更易读；类型变换才是模板 metafunction 的主要价值。
}

TEST(TypeLists, PartialSpecializationCanDecomposeAndTransformATypeSequence) {
  using Source = TypeList<int, double, std::string>;
  using Pointers = typename TransformList<Source, std::add_pointer>::type;

  static_assert(ListSize<Source>::value == 3);
  static_assert(std::is_same_v<typename Front<Source>::type, int>);
  static_assert(std::is_same_v<Pointers, TypeList<int*, double*, std::string*>>);
  SUCCEED();

  // TypeList 本身不存对象，只把类型 pack 包装成可 partial specialize 的形状。Front 对
  // 空列表没有定义，调用方若需要友好失败，应另加 constraint 或检测层。
}

TEST(LazyMetafunctions, UnselectedBranchDoesNotInstantiateAnInvalidTail) {
  static_assert(!LazyAll<std::false_type, HasNoValueMember>::value);
  static_assert(LazyAll<std::true_type, std::true_type>::value);
  SUCCEED();

  // 第一个条件为 false 时 conditional_t 选择 false_type，LazyAll<HasNoValueMember>
  // 不被实例化。模板元编程的惰性选择可保护昂贵或本来无效的后续计算。
}

TEST(IntegerSequences, TurnsCompileTimeIndexesIntoAPack) {
  constexpr auto values = squares(std::make_index_sequence<5>{});
  static_assert(values == std::array<std::size_t, 5>{0, 1, 4, 9, 16});
  EXPECT_EQ(values[3], 9U);

  // index_sequence 把 0..N-1 表示为非类型参数 pack，常用于按索引展开 tuple、array
  // 或构造函数参数。make_index_sequence 负责生成序列，函数模板负责消费它。
}

TEST(DependentFalse, DelaysAnUnsupportedTypeDiagnosticUntilInstantiation) {
  EXPECT_EQ(category_name<int>(), "integral");
  EXPECT_EQ(category_name<double>(), "floating point");

  // dependent_false_v<Value> 只在选中 else 且实例化具体 Value 时求值；因此支持分支可用，
  // 不支持分支会在真正误用的位置给出明确 static_assert 诊断。
}

}  // namespace
