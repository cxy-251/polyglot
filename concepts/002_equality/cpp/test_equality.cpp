// 横向概念 002｜值相等、对象身份与数值特例。
// 共同问题：跨数值类型是否转换；NaN 和负零如何比较；集合按内容还是身份比较；
// 自定义类型如何提供值语义。
//
// polyglot-concept: equality
// polyglot-related: languages/cpp/language/test_010_operator_overloading_conversions_and_spaceship.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <limits>
#include <string>
#include <vector>

namespace {

template <typename Left, typename Right>
concept EqualityComparable = requires(Left left, Right right) {
  { left == right } -> std::convertible_to<bool>;
};

struct Version {
  int major;
  int minor;

  bool operator==(const Version&) const = default;
};

TEST(EqualityConcept, NumericEqualityUsesTypedConversionsAndIeeeSpecialCases) {
  double nan = std::numeric_limits<double>::quiet_NaN();

  EXPECT_TRUE(1 == 1.0);
  EXPECT_FALSE(nan == nan);
  EXPECT_TRUE(0.0 == -0.0);
  static_assert(!EqualityComparable<int, std::string>);
}

TEST(EqualityConcept, ContainersCompareValuesWhileAddressesRepresentIdentity) {
  std::vector<int> first{1, 2};
  std::vector<int> same_value{1, 2};
  std::vector<int>& alias = first;

  EXPECT_EQ(first, same_value);
  EXPECT_NE(&first, &same_value);
  EXPECT_EQ(&first, &alias);
}

TEST(EqualityConcept, DefaultedEqualityDefinesMemberwiseValueSemantics) {
  Version stable{20, 0};
  Version same{20, 0};
  Version newer{23, 0};

  EXPECT_EQ(stable, same);
  EXPECT_NE(stable, newer);

  // 与 Python 的运行期 NotImplemented fallback 不同，不受支持的类型组合在编译期非法。
}

}  // namespace
