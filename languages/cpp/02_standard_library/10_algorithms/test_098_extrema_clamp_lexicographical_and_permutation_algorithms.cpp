// polyglot-covers:
// - cpp.stdlib.algorithms.min-max-and-reference-lifetime
// - cpp.stdlib.algorithms.minmax-and-equivalent-argument-selection
// - cpp.stdlib.algorithms.min-max-element-and-tie-selection
// - cpp.stdlib.algorithms.ranges-extrema-projection
// - cpp.stdlib.algorithms.clamp-bounds-and-returned-reference
// - cpp.stdlib.algorithms.lexicographical-compare-first-difference-and-prefix
// - cpp.stdlib.algorithms.lexicographical-compare-three-way-category
// - cpp.stdlib.algorithms.is-permutation-multiplicity
// - cpp.stdlib.algorithms.next-permutation-cycle-and-result
// - cpp.stdlib.algorithms.prev-permutation-and-custom-order

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <compare>
#include <functional>
#include <ranges>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(MinMax, TwoArgumentFormsReturnReferencesToSelectedArguments) {
  int low = 3;
  int high = 9;

  const int& minimum = std::min(low, high);
  const int& maximum = std::max(low, high);

  EXPECT_EQ(&minimum, &low);
  EXPECT_EQ(&maximum, &high);

  low = 4;
  EXPECT_EQ(minimum, 4);

  // 两参数 min/max 返回 const 引用，不复制选中对象。传临时量并把结果保存为引用会在
  // 完整表达式结束后悬空；需要跨语句保存时按值接收。
}

TEST(MinMax, InitializerListFormsReturnValuesAndAcceptSeveralCandidates) {
  auto minimum = std::min({8, 3, 5, 3});
  auto maximum = std::max({8, 3, 5, 3});

  static_assert(std::is_same_v<decltype(minimum), int>);
  EXPECT_EQ(minimum, 3);
  EXPECT_EQ(maximum, 8);

  // initializer_list overload 按值返回，避免引用列表临时元素；列表必须非空。
}

TEST(Minmax, EquivalentArgumentsChooseFirstForMinAndSecondForMax) {
  struct Item {
    int key;
    char id;
  };
  Item first{7, 'a'};
  Item second{7, 'b'};

  auto result = std::minmax(first, second, [](const Item& left, const Item& right) {
    return left.key < right.key;
  });

  EXPECT_EQ(&result.first, &first);
  EXPECT_EQ(&result.second, &second);

  // 两参数等价时 minmax 的 first 引用第一个参数，second 引用第二个参数；pair 本身并
  // 不延长临时实参生命周期。
}

TEST(MinmaxElement, TiesUseFirstMinimumButLastMaximum) {
  struct Item {
    int key;
    char id;
  };
  const std::vector<Item> items{{1, 'a'}, {5, 'b'}, {1, 'c'}, {5, 'd'}, {3, 'e'}};

  auto result = std::ranges::minmax_element(items, std::less<>{}, &Item::key);

  EXPECT_EQ(result.min->id, 'a');
  EXPECT_EQ(result.max->id, 'd');

  // minmax_element 返回第一个最小项与最后一个最大项；这和分别调用 min_element、
  // max_element 都取首个等价极值的组合并不完全相同。
}

TEST(ExtremaElements, EmptyRangeReturnsEndForBothSearches) {
  const std::vector<int> empty;

  EXPECT_EQ(std::ranges::min_element(empty), empty.end());
  EXPECT_EQ(std::ranges::max_element(empty), empty.end());

  // element 算法通过 end 表达“没有元素”，而 ranges::min(range) 等按值极值算法要求
  // range 非空。调用者必须按接口区分这两类空范围语义。
}

TEST(RangesExtrema, ProjectionSelectsARecordFieldButReturnsTheWholeValue) {
  struct Quote {
    std::string symbol;
    int price;
  };
  const std::array<Quote, 3> quotes{{{"A", 30}, {"B", 10}, {"C", 20}}};

  auto cheapest = std::ranges::min(quotes, std::less<>{}, &Quote::price);
  auto most_expensive = std::ranges::max_element(
      quotes, std::less<>{}, &Quote::price);

  EXPECT_EQ(cheapest.symbol, "B");
  ASSERT_NE(most_expensive, quotes.end());
  EXPECT_EQ(most_expensive->symbol, "A");

  // ranges::min(range) 返回 Quote 值，max_element 返回指向原范围的 iterator；projection
  // 只决定比较键，不把结果类型变成 price。
}

TEST(Clamp, ItReturnsTheValueOrTheNearestInclusiveBoundary) {
  const int low = 10;
  const int high = 20;
  const int inside = 15;
  const int below = 3;
  const int above = 30;

  EXPECT_EQ(&std::clamp(inside, low, high), &inside);
  EXPECT_EQ(&std::clamp(below, low, high), &low);
  EXPECT_EQ(&std::clamp(above, low, high), &high);

  // clamp 返回 v、lo、hi 三者之一的 const 引用；边界是闭区间。要求 high 不排在 low
  // 之前，反向边界违反前置条件而不是自动交换。
}

TEST(Clamp, CopyTheResultWhenAnyCandidateMayBeTemporary) {
  const int bounded = std::clamp(50, 0, 100);

  EXPECT_EQ(bounded, 50);

  // 三个实参都是临时量时结果引用只活到该完整表达式结束；这里按值复制是安全写法。
  // `const int& dangling = std::clamp(50, 0, 100);` 随后使用会悬空，不能写测试执行它。
}

TEST(LexicographicalCompare, FirstDifferenceDeterminesTheOrder) {
  const std::string left = "alpha";
  const std::string right = "alpine";

  EXPECT_TRUE(std::lexicographical_compare(
      left.begin(), left.end(), right.begin(), right.end()));
  EXPECT_FALSE(std::lexicographical_compare(
      right.begin(), right.end(), left.begin(), left.end()));

  // 前三项相同，随后 'h'<'i' 决定结果；后面的字符不再参与。规则与字典顺序相似，但
  // 实际次序完全由元素 comparator 决定，不自动采用语言区域规则。
}

TEST(LexicographicalCompare, AProperPrefixOrdersBeforeTheLongerSequence) {
  const std::array<int, 2> prefix{1, 2};
  const std::array<int, 3> longer{1, 2, 0};

  EXPECT_TRUE(std::ranges::lexicographical_compare(prefix, longer));
  EXPECT_FALSE(std::ranges::lexicographical_compare(longer, prefix));

  // 所有已比较元素等价时，先结束的较短 range 更小；两个完全等价 range 互不小于。
}

TEST(LexicographicalCompareThreeWay, ItReturnsAComparisonCategory) {
  const std::array<int, 3> left{1, 2, 3};
  const std::array<int, 3> right{1, 2, 4};

  auto order = std::lexicographical_compare_three_way(
      left.begin(), left.end(), right.begin(), right.end());

  static_assert(std::is_same_v<decltype(order), std::strong_ordering>);
  EXPECT_TRUE(order < 0);

  // C++20 three-way 版本保留比较类别，可区分 strong/weak/partial ordering；普通 bool
  // 版本只回答第一路是否更小。
}

TEST(IsPermutation, ItComparesMultiplicityWithoutRequiringTheSameOrder) {
  const std::array<int, 5> first{1, 2, 2, 3, 4};
  const std::array<int, 5> reordered{4, 2, 1, 3, 2};
  const std::array<int, 5> wrong_count{4, 2, 1, 3, 3};

  EXPECT_TRUE(std::ranges::is_permutation(first, reordered));
  EXPECT_FALSE(std::ranges::is_permutation(first, wrong_count));

  // permutation 比较每个等价类的出现次数；只比较“包含哪些不同值”会漏掉重复数量。
}

TEST(NextPermutation, ItAdvancesLexicographicallyAndReportsWhetherOneExists) {
  std::array<int, 3> values{1, 2, 3};

  auto first = std::ranges::next_permutation(values);
  EXPECT_TRUE(first.found);
  EXPECT_EQ(first.in, values.end());
  EXPECT_EQ(values, (std::array<int, 3>{1, 3, 2}));

  // found=true 表示得到严格更大的下一排列；in 是最终 end iterator。
}

TEST(NextPermutation, LastPermutationWrapsToTheFirstAndReturnsFalse) {
  std::array<int, 3> values{3, 2, 1};

  auto result = std::ranges::next_permutation(values);

  EXPECT_FALSE(result.found);
  EXPECT_EQ(values, (std::array<int, 3>{1, 2, 3}));

  // 已在最大排列时算法会重排为最小排列并返回 false，不是保持原值。枚举所有排列时
  // 常用 do/while，且起始 range 应先排序，重复元素会自然减少不同排列数量。
}

TEST(PrevPermutation, ItUsesTheProvidedOrderingInTheOppositeDirection) {
  std::array<int, 3> values{3, 1, 2};

  auto result = std::ranges::prev_permutation(values);

  EXPECT_TRUE(result.found);
  EXPECT_EQ(values, (std::array<int, 3>{2, 3, 1}));

  std::array<int, 3> descending_first{3, 2, 1};
  auto under_greater = std::ranges::next_permutation(
      descending_first, std::greater<>{});
  EXPECT_TRUE(under_greater.found);
  EXPECT_EQ(descending_first, (std::array<int, 3>{3, 1, 2}));

  // next/prev 的方向相对于 comparator 定义的字典序；换成 greater 后，“第一排列”是
  // 数值降序，不能再用默认 less 的直觉解释 found。
}

}  // namespace
