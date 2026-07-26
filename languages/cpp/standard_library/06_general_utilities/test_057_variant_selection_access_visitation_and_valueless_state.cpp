// polyglot-covers:
// - cpp.stdlib.utility.variant-default-alternative-and-monostate
// - cpp.stdlib.utility.variant-converting-alternative-selection
// - cpp.stdlib.utility.variant-in-place-and-emplace
// - cpp.stdlib.utility.variant-index-size-and-alternative-traits
// - cpp.stdlib.utility.variant-get-get-if-and-holds-alternative
// - cpp.stdlib.utility.bad-variant-access
// - cpp.stdlib.utility.variant-single-and-multiple-visitation
// - cpp.stdlib.utility.variant-overloaded-visitor-pattern
// - cpp.stdlib.utility.variant-valueless-by-exception
// - cpp.stdlib.utility.variant-comparison-hash-and-swap
// - cpp.stdlib.utility.variant-duplicate-type-index-access

#include <gtest/gtest.h>

#include <functional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace {

struct NoDefault {
  NoDefault() = delete;
  explicit NoDefault(int value) : value(value) {}
  int value;
};

struct ThrowOnMove {
  ThrowOnMove() = default;
  ThrowOnMove(const ThrowOnMove&) = delete;
  ThrowOnMove& operator=(const ThrowOnMove&) = delete;

  ThrowOnMove(ThrowOnMove&&) {
    throw std::runtime_error{"move construction failed"};
  }

  ThrowOnMove& operator=(ThrowOnMove&&) = default;
};

template <typename... Callables>
struct Overloaded : Callables... {
  using Callables::operator()...;
};

template <typename... Callables>
Overloaded(Callables...) -> Overloaded<Callables...>;

TEST(Variant, DefaultConstructionUsesTheFirstAlternative) {
  std::variant<int, std::string> numeric;
  std::variant<std::monostate, NoDefault> maybe_value;

  EXPECT_TRUE(std::holds_alternative<int>(numeric));
  EXPECT_EQ(std::get<int>(numeric), 0);
  EXPECT_TRUE(std::holds_alternative<std::monostate>(maybe_value));
  static_assert(!std::is_default_constructible_v<std::variant<NoDefault, int>>);

  // variant 没有 optional 那样的固有空状态，默认构造始终尝试构造第一个
  // alternative。需要显式“无值”时常把 monostate 放在第一位，同时也使 variant 可默认构造。
}

TEST(Variant, ConvertingConstructorSelectsOneNonNarrowingAlternative) {
  std::variant<int, double> real = 2.5;
  std::variant<float, long> integer = 7;

  EXPECT_TRUE(std::holds_alternative<double>(real));
  EXPECT_DOUBLE_EQ(std::get<double>(real), 2.5);
  EXPECT_TRUE(std::holds_alternative<long>(integer));
  EXPECT_EQ(std::get<long>(integer), 7L);

  // converting constructor 用一组假想 overload 选唯一 alternative，并排除窄化转换。
  // int 到 float 在这个选择中视为 narrowing，所以第二个 variant 选 long；若多个候选同样好则构造不合法。
}

TEST(Variant, InPlaceAndEmplaceChooseATypeOrAnIndexExplicitly) {
  std::variant<int, std::vector<int>, std::string> value{
      std::in_place_type<std::vector<int>>,
      3,
      9,
  };

  ASSERT_TRUE(std::holds_alternative<std::vector<int>>(value));
  EXPECT_EQ(std::get<1>(value), (std::vector<int>{9, 9, 9}));

  std::string& text = value.emplace<2>(4, 'x');
  EXPECT_EQ(&text, &std::get<std::string>(value));
  EXPECT_EQ(text, "xxxx");
  EXPECT_EQ(value.index(), 2U);

  // in_place_type/in_place_index 跳过转换选择并直接传递构造参数。emplace
  // 销毁当前 alternative 后构造指定新值，返回新对象引用；原来的指针和引用随即失效。
}

TEST(Variant, SizeAlternativeAndIndexExposeTheDiscriminatedUnionShape) {
  using Value = std::variant<int, const double, std::string>;

  static_assert(std::variant_size_v<Value> == 3);
  static_assert(std::is_same_v<std::variant_alternative_t<0, Value>, int>);
  static_assert(
      std::is_same_v<std::variant_alternative_t<1, Value>, const double>);
  static_assert(
      std::is_same_v<std::variant_alternative_t<2, const Value>, const std::string>);

  Value value{std::in_place_index<1>, 3.5};
  EXPECT_EQ(value.index(), 1U);

  // variant_alternative 保留 alternative 本身的 cv，并再传播 variant 对象的 cv。
  // index 是从 0 开始的运行期 discriminator；只在 valueless 状态才等于 variant_npos。
}

TEST(Variant, GetThrowsForTheWrongAlternativeWhileGetIfReturnsNull) {
  std::variant<int, std::string> value{std::string{"ready"}};

  EXPECT_TRUE(std::holds_alternative<std::string>(value));
  EXPECT_EQ(std::get<std::string>(value), "ready");
  EXPECT_THROW((void)std::get<int>(value), std::bad_variant_access);
  EXPECT_EQ(std::get_if<int>(&value), nullptr);

  const std::string* text = std::get_if<std::string>(&value);
  ASSERT_NE(text, nullptr);
  EXPECT_EQ(*text, "ready");

  // get<T/I> 是经过检查的引用访问，alternative 不匹配会抛 bad_variant_access。
  // get_if 接受 variant 指针，不匹配或传入空指针都返回 nullptr，适合不把分支失败当异常的代码。
}

TEST(Variant, OverloadedVisitorHandlesEveryAlternativeWithOneObject) {
  using Message = std::variant<int, std::string>;
  const auto describe = Overloaded{
      [](int value) { return "number:" + std::to_string(value); },
      [](const std::string& value) { return "text:" + value; },
  };

  EXPECT_EQ(std::visit(describe, Message{12}), "number:12");
  EXPECT_EQ(
      std::visit(describe, Message{std::string{"ok"}}),
      "text:ok");

  // std::visit 根据运行期 index 选中调用，但 visitor 必须在编译期对所有
  // alternative 都可调用。Overloaded 通过多继承合并 lambda overload，不需要在一个 generic lambda 里手写 type switch。
}

TEST(Variant, MultiVariantVisitInstantiatesTheCartesianProductOfAlternatives) {
  const std::variant<int, double> left{3};
  const std::variant<int, double> right{2.5};

  const double sum = std::visit(
      [](auto first, auto second) -> double {
        return static_cast<double>(first) + static_cast<double>(second);
      },
      left,
      right);
  EXPECT_DOUBLE_EQ(sum, 5.5);

  // 多 variant visit 会为 alternatives 的笛卡尔积检查调用，这里是四种类型组合。
  // visitor 不能只对当前运行期组合有效；显式统一返回类型也可避免不同分支结果不一致。
}

TEST(Variant, ThrowingMoveAssignmentCanCreateTheValuelessState) {
  std::variant<int, ThrowOnMove> target{42};
  std::variant<int, ThrowOnMove> source{std::in_place_index<1>};

  EXPECT_THROW(target = std::move(source), std::runtime_error);
  EXPECT_TRUE(target.valueless_by_exception());
  EXPECT_EQ(target.index(), std::variant_npos);
  EXPECT_THROW(
      (void)std::visit([](const auto&) {}, target),
      std::bad_variant_access);

  // 目标先销毁 int，再移动构造新 alternative；构造抛异常后已无旧值可恢复，
  // 因此进入 valueless_by_exception。这是异常恢复状态，不应被当成 variant 的常规“空值”建模。
}

TEST(Variant, ComparisonUsesIndexFirstAndHashIncludesTheActiveAlternative) {
  using Value = std::variant<int, std::string>;
  Value numeric{std::in_place_type<int>, 999};
  Value text{std::in_place_type<std::string>, "a"};
  const Value numeric_copy = numeric;

  EXPECT_LT(numeric, text);
  EXPECT_EQ(numeric, numeric_copy);
  EXPECT_EQ(std::hash<Value>{}(numeric), std::hash<Value>{}(numeric_copy));

  std::swap(numeric, text);
  EXPECT_TRUE(std::holds_alternative<std::string>(numeric));
  EXPECT_TRUE(std::holds_alternative<int>(text));

  // 两个 variant 的 index 不同时先比 index，不会把 int 999 与 string "a" 做跨类型
  // 比较。hash 必须区分 alternative 和其值，具体组合公式未指定，只能依赖相等 variant 产生相等 hash。
}

TEST(Variant, DuplicateAlternativeTypesRequireIndexBasedOperations) {
  std::variant<int, int> duplicated{std::in_place_index<1>, 17};

  EXPECT_EQ(duplicated.index(), 1U);
  EXPECT_EQ(std::get<1>(duplicated), 17);
  duplicated.emplace<0>(8);
  EXPECT_EQ(std::get<0>(duplicated), 8);

  // variant 允许重复 alternative type，但此时 get<int>、holds_alternative<int> 和
  // emplace<int> 都不合法，因为 T 必须恰好出现一次。索引 API 是这种建模的唯一无歧义入口。
}

}  // namespace
