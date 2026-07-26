// polyglot-covers:
// - cpp.stdlib.ranges.join-view-flattens-one-nesting-level
// - cpp.stdlib.ranges.join-view-reference-mutation-and-empty-inner-ranges
// - cpp.stdlib.ranges.join-view-category-and-size-loss
// - cpp.stdlib.ranges.join-view-prvalue-inner-range-version-evolution
// - cpp.stdlib.ranges.split-view-single-element-delimiter
// - cpp.stdlib.ranges.split-view-range-pattern-delimiter
// - cpp.stdlib.ranges.split-view-consecutive-and-trailing-delimiter-semantics
// - cpp.stdlib.ranges.split-view-yields-nonowning-subranges
// - cpp.stdlib.ranges.split-then-transform-workflow

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <std::ranges::input_range Range>
auto CollectValues(Range&& range) {
  std::vector<std::ranges::range_value_t<Range>> result;
  std::ranges::copy(range, std::back_inserter(result));
  return result;
}

template <std::ranges::input_range Tokens>
std::vector<std::string> CollectTokens(Tokens&& tokens) {
  std::vector<std::string> result;
  for (auto&& token : tokens) {
    std::string owned;
    std::ranges::copy(token, std::back_inserter(owned));
    result.push_back(std::move(owned));
  }
  return result;
}

template <class Range>
concept CanJoin = requires(Range&& range) {
  std::views::join(std::forward<Range>(range));
};

TEST(JoinView, ItFlattensExactlyOneLevelAndSkipsEmptyInnerRanges) {
  std::vector<std::vector<int>> nested{{1, 2}, {}, {3}, {4, 5}};
  auto flattened = nested | std::views::join;

  EXPECT_EQ(CollectValues(flattened), (std::vector<int>{1, 2, 3, 4, 5}));

  // join 遍历 outer 的每个 inner range，并在 inner 到达 end 后切换下一项；空 inner
  // 自动跳过。它只压平一层，更深嵌套需要再次 join 或显式递归。
}

TEST(JoinView, LvalueInnerRangesExposeWritableUnderlyingReferences) {
  std::vector<std::vector<int>> nested{{1, 2}, {3}};
  auto flattened = nested | std::views::join;

  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(flattened)>,
                int&>);

  for (int& value : flattened) {
    value *= 10;
  }

  EXPECT_EQ(nested, (std::vector<std::vector<int>>{{10, 20}, {30}}));

  // outer 解引用得到 vector<int>& 时，join 继续返回 inner 的 int&，所以修改写回嵌套容器。
  // outer 或 inner 的结构性修改可能让保存的两层 iterator 同时失效。
}

TEST(JoinView, FlatteningLosesRandomAccessAndCheapTotalSize) {
  std::vector<std::vector<int>> nested{{1, 2}, {3, 4}};
  auto flattened = nested | std::views::join;

  static_assert(std::ranges::bidirectional_range<decltype(flattened)>);
  static_assert(!std::ranges::random_access_range<decltype(flattened)>);
  static_assert(!std::ranges::sized_range<decltype(flattened)>);
  EXPECT_EQ(std::ranges::distance(flattened), 4);

  // 定位第 n 个扁平元素必须跨越长度不同的 inner range，总 size 也需累加；即使两层
  // vector 都随机访问且有 size，join 不承诺 random access 或 sized_range。
}

TEST(JoinView, PrvalueInnerRangeSupportDependsOnAppliedStandardRepair) {
  auto generated = std::views::iota(1, 3) |
                   std::views::transform([](int value) {
                     return std::vector<int>{value, value * 10};
                   });
  constexpr bool supports_prvalue_inner = CanJoin<decltype(generated)>;

  if constexpr (supports_prvalue_inner) {
    SUCCEED() << "implementation accepts prvalue inner ranges";
  } else {
    SUCCEED() << "implementation follows the original C++20 lvalue-inner restriction";
  }

  // 原始 C++20 join_view 对 prvalue inner range 的支持有限，后续缺陷修订增加内部缓存；
  // 实现可能回溯。表达式检测记录能力，不能假定 transform 生成临时容器总能直接 join。
}

TEST(SplitView, ElementDelimiterProducesSubrangesWithoutTheDelimiter) {
  std::string text = "alpha,beta,gamma";
  auto tokens = text | std::views::split(',');

  EXPECT_EQ(
      CollectTokens(tokens),
      (std::vector<std::string>{"alpha", "beta", "gamma"}));

  using TokenReference = std::ranges::range_reference_t<decltype(tokens)>;
  static_assert(std::ranges::forward_range<TokenReference>);

  // split 外层逐段产生 inner range，delimiter 不属于任何段。段只是 text 的 iterator
  // 边界，不分配 string；CollectTokens 才显式把每段物化成 owning string。
}

TEST(SplitView, ARangePatternCanContainMultipleElements) {
  const std::string_view text = "left--middle--right";
  const std::string_view delimiter = "--";
  auto tokens = text | std::views::split(delimiter);

  EXPECT_EQ(
      CollectTokens(tokens),
      (std::vector<std::string>{"left", "middle", "right"}));

  // pattern 本身也是 view，可包含多个元素；split 查找整个连续子序列而非任意一个字符。
  // delimiter view 的底层存储也必须在 tokens 遍历期间有效，本例都指向字符串字面量。
}

TEST(SplitView, ConsecutiveDelimitersProduceEmptySegmentsButTrailingDoesNot) {
  const std::string_view text = "a,,b,";
  auto tokens = text | std::views::split(',');

  EXPECT_EQ(
      CollectTokens(tokens),
      (std::vector<std::string>{"a", "", "b"}));

  // 相邻 delimiter 之间会产生空段；但 delimiter 恰好结束于 base.end() 时，outer iterator
  // 也立即到 end，不再产生尾部空段。解析 CSV 时不能直接假定 split 保留最后空字段。
}

TEST(SplitView, SegmentIteratorsAliasTheOriginalMutableCharacters) {
  std::string text = "ab,cd";
  auto tokens = text | std::views::split(',');
  auto first_token = *tokens.begin();

  *first_token.begin() = 'A';

  EXPECT_EQ(text, "Ab,cd");

  // split 的 inner range 引用原字符，非 const string 因而可写；任何导致 string 重分配
  // 的操作都会让 token iterator 悬空。要长期保存字段应复制成独立 string。
}

TEST(SplitWorkflow, TransformCanMapEachSubrangeToAnOwnedOrComputedResult) {
  const std::string_view text = "2|3|5";
  auto lengths = text |
                 std::views::split('|') |
                 std::views::transform([](auto token) {
                   return static_cast<int>(std::ranges::distance(token));
                 });

  EXPECT_EQ(CollectValues(lengths), (std::vector<int>{1, 1, 1}));

  // split 常与 transform 组合，把非拥有 token 转成长度、数字或 owning string；转换仍是
  // 惰性的。若返回 string_view，必须确保原 text 寿命覆盖所有后续使用。
}

}  // namespace
