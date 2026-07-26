// polyglot-covers:
// - cpp.stdlib.ranges.elements-view-tuple-index-projection
// - cpp.stdlib.ranges.elements-view-reference-and-value-types
// - cpp.stdlib.ranges.elements-view-mutable-projected-member
// - cpp.stdlib.ranges.elements-view-preserved-size-and-navigation
// - cpp.stdlib.ranges.views-keys-alias-for-elements-zero
// - cpp.stdlib.ranges.views-values-alias-for-elements-one
// - cpp.stdlib.ranges.map-keys-const-and-values-mutable-through-views
// - cpp.stdlib.ranges.elements-view-composition-with-filter-transform

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <map>
#include <ranges>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <std::ranges::input_range Range>
auto CollectElements(Range&& range) {
  std::vector<std::ranges::range_value_t<Range>> result;
  std::ranges::copy(range, std::back_inserter(result));
  return result;
}

TEST(ElementsView, IndexSelectsOneTupleLikeComponentFromEveryElement) {
  std::vector<std::tuple<int, std::string, double>> records{
      {1, "Ada", 9.5},
      {2, "Grace", 8.5},
  };
  auto names = records | std::views::elements<1>;

  EXPECT_EQ(CollectElements(names),
            (std::vector<std::string>{"Ada", "Grace"}));

  // elements<N> 对每个 range reference 调用 get<N>，N 是编译期索引；它不会复制完整
  // tuple。所有元素类型都必须支持该 get，越界索引会在约束/实例化阶段被拒绝。
}

TEST(ElementsView, ReferenceAndValueTypesComeFromTheSelectedComponent) {
  using Records = std::vector<std::pair<int, std::string>>;
  Records records{{1, "one"}};
  auto names = records | std::views::elements<1>;

  static_assert(std::is_same_v<
                std::ranges::range_value_t<decltype(names)>,
                std::string>);
  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(names)>,
                std::string&>);
  EXPECT_EQ(names.front(), "one");

  // value_type 是 tuple_element_t<N,range_value_t<V>>，reference 来自 get<N>(*it)；
  // 对 lvalue pair 因而是 string&，不是 pair 的复制品。
}

TEST(ElementsView, MutableSelectedReferencesWriteBackToTheTupleLikeSource) {
  std::vector<std::pair<int, std::string>> records{{1, "one"}, {2, "two"}};
  auto names = records | std::views::elements<1>;

  names.front() = "ONE";
  for (std::string& name : names) {
    name += "!";
  }

  EXPECT_EQ(records[0].second, "ONE!");
  EXPECT_EQ(records[1].second, "two!");

  // elements_view 保留选中成员的引用限定，可用它批量修改 mapped/tuple 字段；
  // 结构性修改 records 仍可能使 view iterator 失效。
}

TEST(ElementsView, OneToOneProjectionPreservesRandomAccessAndSize) {
  std::vector<std::pair<int, std::string>> records{{1, "one"}, {2, "two"}};
  auto ids = records | std::views::elements<0>;

  static_assert(std::ranges::random_access_range<decltype(ids)>);
  static_assert(std::ranges::sized_range<decltype(ids)>);
  static_assert(std::ranges::common_range<decltype(ids)>);
  static_assert(!std::ranges::contiguous_range<decltype(ids)>);

  EXPECT_EQ(ids.size(), records.size());
  EXPECT_EQ(ids[1], 2);

  // 每个输入恰好对应一个投影值，因此保留 size 和导航；但相邻 pair 的 first 子对象
  // 并不组成连续 int 数组，所以 elements_view 不能声称 contiguous_range。
}

TEST(KeysValuesViews, TheyAreReadableAliasesForElementsZeroAndOne) {
  std::vector<std::pair<int, std::string>> records{{1, "one"}, {2, "two"}};
  auto keys = records | std::views::keys;
  auto values = records | std::views::values;

  EXPECT_EQ(CollectElements(keys), (std::vector<int>{1, 2}));
  EXPECT_EQ(CollectElements(values),
            (std::vector<std::string>{"one", "two"}));

  static_assert(std::is_same_v<
                decltype(keys),
                decltype(records | std::views::elements<0>)>);
  static_assert(std::is_same_v<
                decltype(values),
                decltype(records | std::views::elements<1>)>);

  // views::keys/values 分别是 elements<0>/<1> 的语义化 adaptor，适用于 pair-like range，
  // 不只限于 map。名字能让查询管道的意图更清楚。
}

TEST(KeysValuesViews, MapKeysRemainConstWhileMappedValuesRemainWritable) {
  std::map<std::string, int> scores{{"Ada", 10}, {"Grace", 20}};
  auto keys = scores | std::views::keys;
  auto values = scores | std::views::values;

  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(keys)>,
                const std::string&>);
  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(values)>,
                int&>);

  for (int& score : values) {
    score += 1;
  }
  EXPECT_EQ(scores.at("Ada"), 11);
  EXPECT_EQ(scores.at("Grace"), 21);

  // map 的 value_type 是 pair<const Key,T>，keys view 不能绕过树键不可修改规则；
  // values view 则安全暴露 T&，修改不会破坏排序结构。
}

TEST(ElementsView, ItComposesWithFilteringAndTransformationOfProjectedValues) {
  std::vector<std::pair<std::string, int>> scores{
      {"Ada", 10},
      {"Bjarne", 21},
      {"Grace", 30},
  };
  auto doubled_even_scores = scores |
                             std::views::values |
                             std::views::filter([](int score) {
                               return score % 2 == 0;
                             }) |
                             std::views::transform([](int score) {
                               return score * 2;
                             });

  EXPECT_EQ(CollectElements(doubled_even_scores),
            (std::vector<int>{20, 60}));

  // 先 values 投影可让后续谓词只关心 int；整个管道仍惰性引用 scores。若需要 key 与
  // value 同时参与判断，就应在投影前 filter pair，而不是事后尝试找回 key。
}

}  // namespace
