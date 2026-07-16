// polyglot-covers:
// - cpp.stdlib.language-support.strong-ordering
// - cpp.stdlib.language-support.weak-ordering
// - cpp.stdlib.language-support.partial-ordering
// - cpp.stdlib.language-support.comparison-category-predicates
// - cpp.stdlib.language-support.common-comparison-category
// - cpp.stdlib.language-support.compare-three-way
// - cpp.stdlib.language-support.named-comparison-customization-points
// - cpp.stdlib.language-support.comparison-fallback-functions

#include <gtest/gtest.h>

#include <compare>
#include <cmath>
#include <limits>
#include <string>
#include <type_traits>

namespace {

struct CaseInsensitiveText {
  std::string value;

  friend bool operator==(const CaseInsensitiveText& left, const CaseInsensitiveText& right) {
    return normalize(left.value) == normalize(right.value);
  }

  friend bool operator<(const CaseInsensitiveText& left, const CaseInsensitiveText& right) {
    return normalize(left.value) < normalize(right.value);
  }

 private:
  static std::string normalize(std::string text) {
    for (char& character : text) {
      if (character >= 'A' && character <= 'Z') {
        character = static_cast<char>(character - 'A' + 'a');
      }
    }
    return text;
  }
};

struct Version {
  int major;
  int minor;

  auto operator<=>(const Version&) const = default;
};

TEST(ComparisonCategories, StrongWeakAndPartialCategoriesCarryDifferentGuarantees) {
  constexpr auto strong = 3 <=> 5;
  constexpr auto weak = std::weak_ordering::equivalent;
  const auto partial = 0.0 <=> std::numeric_limits<double>::quiet_NaN();

  static_assert(std::is_same_v<decltype(strong), const std::strong_ordering>);
  EXPECT_TRUE(strong < 0);
  EXPECT_TRUE(weak == 0);
  EXPECT_TRUE(partial == std::partial_ordering::unordered);

  // category 对象只与字面量 0 比较，不是任意整数。strong 的 equivalent 意味着可替换的
  // 相等；weak 允许同一等价类中表示不同；partial 还允许 unordered，例如 NaN。
}

TEST(ComparisonPredicates, NamedPredicatesAlsoHandleUnorderedResults) {
  const auto less = Version{1, 4} <=> Version{2, 0};
  const auto unordered = 1.0 <=> std::numeric_limits<double>::quiet_NaN();

  EXPECT_TRUE(std::is_lt(less));
  EXPECT_FALSE(std::is_eq(less));
  EXPECT_FALSE(std::is_lt(unordered));
  EXPECT_FALSE(std::is_gt(unordered));
  EXPECT_FALSE(std::is_eq(unordered));

  // is_lt/is_eq 等接受 comparison category 并清楚表达意图。unordered 不是小于、等于或
  // 大于，不能用“不是小于所以大于等于”这种二分逻辑处理 partial ordering。
}

TEST(CommonCategory, ChoosesTheWeakestCategoryAllInputsCanRepresent) {
  using StrongAndWeak =
      std::common_comparison_category_t<std::strong_ordering, std::weak_ordering>;
  using StrongAndPartial =
      std::common_comparison_category_t<std::strong_ordering, std::partial_ordering>;

  static_assert(std::is_same_v<StrongAndWeak, std::weak_ordering>);
  static_assert(std::is_same_v<StrongAndPartial, std::partial_ordering>);
  SUCCEED();

  // 组合成员比较时，整体只能承诺所有成员共同满足的最弱 category。含浮点成员的默认
  // spaceship 因而通常返回 partial_ordering，不能擅自提升成 strong_ordering。
}

TEST(CompareThreeWay, FunctionObjectUsesTheSpaceshipExpression) {
  const std::compare_three_way compare;

  EXPECT_TRUE(compare(Version{1, 2}, Version{1, 3}) < 0);
  EXPECT_TRUE(compare(Version{2, 0}, Version{2, 0}) == 0);
  static_assert(std::three_way_comparable<Version>);

  // compare_three_way 是透明函数对象，适合把三路比较传给泛型设施；类型仍须满足
  // three_way_comparable 的 == 与 <=> 一致性契约，不只是“碰巧存在 operator<=>”。
}

TEST(NamedCustomizationPoints, StrongWeakAndPartialOrderSelectAvailableSemantics) {
  EXPECT_TRUE(std::strong_order(2, 3) < 0);
  EXPECT_TRUE(std::weak_order(2.0, 3.0) < 0);
  EXPECT_TRUE(std::partial_order(2.0, 3.0) < 0);

  // named customization point 会按标准规定寻找定制或内建比较，并要求对应 category。
  // strong_order 不接受不能提供全序的普通浮点语义；weak/partial 适用范围不同。
}

TEST(ComparisonFallback, SynthesizesThreeWayMeaningFromEqualityAndLessThan) {
  const CaseInsensitiveText first{"Alpha"};
  const CaseInsensitiveText equivalent{"alpha"};
  const CaseInsensitiveText later{"Beta"};

  EXPECT_TRUE(std::compare_strong_order_fallback(first, equivalent) == 0);
  EXPECT_TRUE(std::compare_strong_order_fallback(first, later) < 0);
  EXPECT_TRUE(std::compare_strong_order_fallback(later, first) > 0);

  // fallback 先尝试 strong_order 定制，否则由 == 与 < 合成 strong_ordering。只有当旧式
  // 运算确实满足全序契约时才安全；矛盾或非传递的 operator< 不会被库自动修正。
}

}  // namespace
