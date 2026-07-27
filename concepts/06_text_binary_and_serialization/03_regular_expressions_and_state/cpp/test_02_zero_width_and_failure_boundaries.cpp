// 零宽匹配、游标推进与编译失败。
// 共同问题：零宽成功如何避免无限迭代；复用 matcher 是否泄漏游标；
// 非法模式在什么阶段报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_125_regex_grammars_matches_replacement_and_iterators.cpp

#include <gtest/gtest.h>

#include <regex>
#include <string>
#include <vector>

namespace {

TEST(RegexBoundaryConcept, RegexIteratorAdvancesAfterZeroWidthMatches) {
  const std::string text = "ab";
  const std::regex pattern{"(?=.)"};
  std::vector<std::ptrdiff_t> positions;

  for (std::sregex_iterator match{text.begin(), text.end(), pattern}, end;
       match != end;
       ++match) {
    positions.push_back(match->position());
    EXPECT_TRUE(match->str().empty());
  }

  EXPECT_EQ(positions, (std::vector<std::ptrdiff_t>{0, 1}));
}

TEST(RegexBoundaryConcept, MatchStateBelongsToEachAlgorithmResult) {
  const std::regex pattern{"[0-9]"};
  std::smatch first;
  std::smatch second;
  const std::string text = "1a2";

  ASSERT_TRUE(std::regex_search(text, first, pattern));
  ASSERT_TRUE(std::regex_search(first.suffix().first, first.suffix().second, second, pattern));

  EXPECT_EQ(first.str(), "1");
  EXPECT_EQ(second.str(), "2");
  EXPECT_EQ(first.position(), 0);
}

TEST(RegexBoundaryConcept, InvalidPatternThrowsDuringRegexConstruction) {
  EXPECT_THROW(static_cast<void>(std::regex{"("}), std::regex_error);
}

}  // namespace
