// polyglot-covers:
// - cpp.stdlib.functional.default-searcher
// - cpp.stdlib.functional.searcher-call-operator-range
// - cpp.stdlib.functional.search-algorithm-searcher-overload
// - cpp.stdlib.functional.boyer-moore-searcher
// - cpp.stdlib.functional.boyer-moore-horspool-searcher
// - cpp.stdlib.functional.searcher-custom-predicate-and-hash
// - cpp.stdlib.functional.searcher-pattern-lifetime
// - cpp.stdlib.functional.empty-pattern-search

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <functional>
#include <string>

namespace {

constexpr unsigned char ascii_lower(unsigned char character) {
  if (character >= static_cast<unsigned char>('A') &&
      character <= static_cast<unsigned char>('Z')) {
    return static_cast<unsigned char>(character - 'A' + 'a');
  }
  return character;
}

struct CaseInsensitiveEqual {
  bool operator()(char left, char right) const noexcept {
    return ascii_lower(static_cast<unsigned char>(left)) ==
           ascii_lower(static_cast<unsigned char>(right));
  }
};

struct CaseInsensitiveHash {
  std::size_t operator()(char value) const noexcept {
    return std::hash<unsigned char>{}(
        ascii_lower(static_cast<unsigned char>(value)));
  }
};

TEST(DefaultSearcher, CallableReturnsTheWholeMatchedRange) {
  const std::string pattern = "needle";
  const std::string text = "find a needle in a haystack";
  const std::default_searcher searcher{pattern.begin(), pattern.end()};

  const auto match = searcher(text.begin(), text.end());
  ASSERT_NE(match.first, text.end());
  EXPECT_EQ(std::string(match.first, match.second), "needle");
  EXPECT_EQ(std::distance(text.begin(), match.first), 7);

  // searcher 自身的 operator() 返回 [match_first, match_last) pair，因此可直接取得
  // 完整匹配区间。default_searcher 使用与普通 std::search 等价的前向搜索，不预处理跳转表。
}

TEST(DefaultSearcher, SearchAlgorithmOverloadReturnsOnlyTheMatchBeginning) {
  const std::string pattern = "aba";
  const std::string text = "zzabazz";
  const std::default_searcher searcher{pattern.begin(), pattern.end()};

  const auto first = std::search(text.begin(), text.end(), searcher);
  ASSERT_NE(first, text.end());
  EXPECT_EQ(std::distance(text.begin(), first), 2);

  // std::search(first, last, searcher) 适配传统算法接口，只返回匹配起点。
  // 需要结束位置时可直接调用 searcher，或在已知固定 pattern 长度时自行向后移动。
}

TEST(DefaultSearcher, CustomPredicateCanDefineDomainSpecificEquality) {
  const std::string pattern = "Error";
  const std::string text = "status: ERROR detected";
  const std::default_searcher searcher{
      pattern.begin(),
      pattern.end(),
      CaseInsensitiveEqual{},
  };

  const auto match = searcher(text.begin(), text.end());
  ASSERT_NE(match.first, text.end());
  EXPECT_EQ(std::string(match.first, match.second), "ERROR");

  // default_searcher 只需要 predicate，每次按它比较 pattern 和 text 元素。
  // 这里只做 ASCII 折叠，避免把 locale/Unicode 大小写的复杂语义伪装成单字节问题。
}

TEST(BoyerMooreSearcher, PreprocessedPatternSkipsAheadOnMismatches) {
  const std::string pattern = "brown fox";
  const std::string text = "the quick brown fox jumps over the lazy dog";
  const std::boyer_moore_searcher searcher{pattern.begin(), pattern.end()};

  const auto first = std::search(text.begin(), text.end(), searcher);
  ASSERT_NE(first, text.end());
  EXPECT_EQ(std::string(first, first + pattern.size()), pattern);

  // boyer_moore_searcher 在构造时预处理 pattern，利用坏字符与好后缀规则跳过
  // 不可能起点。它要求 random-access iterator，还可能分配预处理存储；短 pattern 不一定比简单搜索更快。
}

TEST(BoyerMooreSearcher, CustomHashMustAgreeWithTheCustomPredicate) {
  const std::string pattern = "Token";
  const std::string text = "prefix-tOkEn-suffix";
  const std::boyer_moore_searcher searcher{
      pattern.begin(),
      pattern.end(),
      CaseInsensitiveHash{},
      CaseInsensitiveEqual{},
  };

  const auto first = std::search(text.begin(), text.end(), searcher);
  ASSERT_NE(first, text.end());
  EXPECT_EQ(std::string(first, first + pattern.size()), "tOkEn");

  // 若 predicate(a, b) 为 true，hash(a) 与 hash(b) 必须相等。只替换大小写无关
  // predicate 却仍用原字符 hash，会破坏搜索器前置条件，不只是降低命中率。
}

TEST(HorspoolSearcher, UsesASmallerBadCharacterOnlyPreprocessingStrategy) {
  const std::string pattern = "abcab";
  const std::string text = "zzzzabcabyyyy";
  const std::boyer_moore_horspool_searcher searcher{
      pattern.begin(),
      pattern.end(),
  };

  const auto match = searcher(text.begin(), text.end());
  ASSERT_NE(match.first, text.end());
  EXPECT_EQ(std::string(match.first, match.second), pattern);

  // Horspool 变体只保留坏字符跳转表，预处理和状态通常更小，但可能比完整
  // Boyer-Moore 做更多对齐尝试。标准约定语义与要求，不承诺某个输入上的固定性能排名。
}

TEST(Searchers, EmptyPatternMatchesAtTheBeginningAndPatternsMustOutliveSearchers) {
  const std::string empty_pattern;
  const std::string text = "content";
  const std::default_searcher searcher{
      empty_pattern.begin(),
      empty_pattern.end(),
  };

  const auto match = searcher(text.begin(), text.end());
  EXPECT_EQ(match.first, text.begin());
  EXPECT_EQ(match.second, text.begin());

  // 空 pattern 在输入开头匹配一个空区间。所有这些 searcher 都保存 pattern
  // iterator 而不拥有 pattern；pattern 容器在 searcher 使用前销毁或重分配，会让内部迭代器悬空。
}

}  // namespace
