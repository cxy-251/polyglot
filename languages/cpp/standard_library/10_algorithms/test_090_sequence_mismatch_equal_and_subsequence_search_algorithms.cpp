// polyglot-covers:
// - cpp.stdlib.algorithms.mismatch-first-difference-and-result-pair
// - cpp.stdlib.algorithms.equal-length-and-element-equivalence
// - cpp.stdlib.algorithms.adjacent-find-first-neighbor-match
// - cpp.stdlib.algorithms.find-first-of-candidate-set
// - cpp.stdlib.algorithms.search-first-subsequence-and-empty-needle
// - cpp.stdlib.algorithms.find-end-last-subsequence
// - cpp.stdlib.algorithms.search-n-consecutive-equal-values
// - cpp.stdlib.algorithms.ranges-search-subrange-result
// - cpp.stdlib.algorithms.two-range-projections
// - cpp.stdlib.algorithms.search-result-lifetime-and-dangling

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <ranges>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct Item {
  int key;
  std::string label;
};

TEST(Mismatch, ItReturnsTheFirstUnequalPositionFromBothRanges) {
  const std::array<int, 5> left{1, 2, 3, 4, 5};
  const std::array<int, 4> right{1, 2, 9, 4};

  auto classic = std::mismatch(left.begin(), left.end(), right.begin(), right.end());
  auto ranged = std::ranges::mismatch(left, right);

  EXPECT_EQ(classic.first, left.begin() + 2);
  EXPECT_EQ(classic.second, right.begin() + 2);
  EXPECT_EQ(ranged.in1, left.begin() + 2);
  EXPECT_EQ(ranged.in2, right.begin() + 2);
  EXPECT_EQ(*ranged.in1, 3);
  EXPECT_EQ(*ranged.in2, 9);

  // mismatch 同步前进两路，在首个不等元素或任一路 end 停止。经典版返回 pair，
  // ranges 版返回具名 in1/in2；完全相同但长度不同时，位置落在较短 range 的 end。
}

TEST(Mismatch, ProjectionsAllowComparingDifferentRecordTypesByACommonKey) {
  const std::vector<Item> records{{1, "one"}, {2, "two"}, {4, "four"}};
  const std::vector<int> expected_keys{1, 2, 3};

  auto result = std::ranges::mismatch(
      records,
      expected_keys,
      std::ranges::equal_to{},
      &Item::key,
      std::identity{});

  ASSERT_NE(result.in1, records.end());
  ASSERT_NE(result.in2, expected_keys.end());
  EXPECT_EQ(result.in1->key, 4);
  EXPECT_EQ(*result.in2, 3);

  // 两路 ranges 算法可分别投影，再把投影结果交给 relation；无需让 Item 与 int
  // 直接定义 operator==，也无需复制 keys。
}

TEST(Equal, BothValuesAndLengthsMustMatch) {
  const std::array<int, 3> first{1, 2, 3};
  const std::array<int, 3> same{1, 2, 3};
  const std::array<int, 4> longer{1, 2, 3, 4};

  EXPECT_TRUE(std::ranges::equal(first, same));
  EXPECT_FALSE(std::ranges::equal(first, longer));

  int calls = 0;
  const bool equal = std::ranges::equal(first, same, [&](int left, int right) {
    ++calls;
    return left == right;
  });
  EXPECT_TRUE(equal);
  EXPECT_EQ(calls, 3);

  // equal 要求所有成对元素等价且长度相同。若两边都是 sized_range，长度不同可在调用
  // predicate 前直接返回 false；不要把“较短前缀相同”误当成 range 相等。
}

TEST(AdjacentFind, ItReturnsTheFirstElementOfTheMatchingNeighborPair) {
  const std::vector<int> values{1, 2, 2, 3, 3};

  auto equal_pair = std::adjacent_find(values.begin(), values.end());
  auto increasing_gap = std::ranges::adjacent_find(values, [](int left, int right) {
    return right - left > 0;
  });

  EXPECT_EQ(equal_pair, values.begin() + 1);
  EXPECT_EQ(increasing_gap, values.begin());

  // adjacent_find 检查相邻 `(i,next(i))` 并返回 i；默认找相等邻居，自定义 binary
  // predicate 可表达任意邻接关系。少于两个元素时直接返回 end。
}

TEST(FindFirstOf, ItFindsTheEarliestHaystackElementPresentInTheCandidateRange) {
  const std::string text = "algorithm";
  const std::string vowels = "aeiou";

  auto first_vowel = std::ranges::find_first_of(text, vowels);

  ASSERT_NE(first_vowel, text.end());
  EXPECT_EQ(*first_vowel, 'a');

  const std::string no_candidates;
  EXPECT_EQ(std::ranges::find_first_of(text, no_candidates), text.end());

  // 返回顺序由第一路 haystack 决定，不是 candidates 中最早出现的值；第二路为空时
  // 没有任何可匹配项。朴素复杂度可达 N*M，大候选集可先改用 hash/set 查询。
}

TEST(Search, ClassicAndRangesFormsLocateTheFirstCompleteSubsequence) {
  const std::string text = "one two two three";
  const std::string needle = "two";

  auto classic = std::search(text.begin(), text.end(), needle.begin(), needle.end());
  auto ranged = std::ranges::search(text, needle);

  EXPECT_EQ(classic, text.begin() + 4);
  EXPECT_EQ(ranged.begin(), text.begin() + 4);
  EXPECT_EQ(ranged.end(), text.begin() + 7);
  EXPECT_EQ(std::string(ranged.begin(), ranged.end()), "two");

  // 经典 search 只返回首位置，匹配末尾需加 needle 长度；ranges::search 返回 subrange
  // `[match_begin,match_end)`，失败时两个边界都等于 text.end()。
}

TEST(Search, EmptyNeedleMatchesAnEmptySubrangeAtTheBeginning) {
  const std::string text = "abc";
  const std::string empty;

  auto result = std::ranges::search(text, empty);

  EXPECT_EQ(result.begin(), text.begin());
  EXPECT_EQ(result.end(), text.begin());
  EXPECT_TRUE(result.empty());

  // 空 pattern 按定义在起点匹配一个空 subrange；这与“找不到”不同，后者返回 end/end。
}

TEST(FindEnd, ItReturnsTheLastCompleteOccurrenceRatherThanTheFirst) {
  const std::string text = "ababa";
  const std::string needle = "aba";

  auto first = std::ranges::search(text, needle);
  auto last = std::ranges::find_end(text, needle);

  EXPECT_EQ(first.begin(), text.begin());
  EXPECT_EQ(last.begin(), text.begin() + 2);
  EXPECT_EQ(last.end(), text.end());

  // find_end 找最后一次完整匹配，重叠也计入；"aba" 在 "ababa" 的位置 0 和 2 重叠。
  // 它不是从 search 结果末尾继续找，否则会漏掉重叠匹配。
}

TEST(SearchN, ItFindsTheFirstRunOfCountEquivalentElements) {
  const std::vector<int> values{1, 7, 7, 2, 7, 7, 7, 3};

  auto three_sevens = std::ranges::search_n(values, 3, 7);
  auto four_sevens = std::ranges::search_n(values, 4, 7);

  EXPECT_EQ(three_sevens.begin(), values.begin() + 4);
  EXPECT_EQ(three_sevens.end(), values.begin() + 7);
  EXPECT_EQ(four_sevens.begin(), values.end());
  EXPECT_EQ(four_sevens.end(), values.end());

  // search_n 要求 count 个连续匹配；总计有五个 7 并不代表存在四连。ranges 版同样
  // 返回完整 subrange，失败为 end/end。
}

TEST(Search, CaseInsensitivePredicateCanDefineElementEquivalence) {
  const std::string text = "Hello WORLD";
  const std::string needle = "world";
  auto ascii_equal = [](unsigned char left, unsigned char right) {
    return std::tolower(left) == std::tolower(right);
  };

  auto result = std::ranges::search(text, needle, ascii_equal);

  ASSERT_NE(result.begin(), text.end());
  EXPECT_EQ(std::string(result.begin(), result.end()), "WORLD");

  // cctype 函数要求 EOF 或可表示为 unsigned char 的值；先用 unsigned char 参数避免
  // 负 signed char 导致未定义行为。真实 Unicode 大小写匹配需要专门文本库。
}

TEST(SearchResult, TemporaryOwnedHaystackProducesADanglingSubrangeMarker) {
  auto result = std::ranges::search(std::string{"abc"}, std::string_view{"b"});

  static_assert(std::is_same_v<decltype(result), std::ranges::dangling>);
  (void)result;

  // search 返回的两条 iterator 都属于第一路 haystack；临时 owning string 销毁后不安全，
  // 所以结果整体变成 dangling。第二路 pattern 的寿命不决定返回类型。
}

}  // namespace
