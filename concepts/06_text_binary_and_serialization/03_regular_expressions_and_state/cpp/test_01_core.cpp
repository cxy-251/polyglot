// 正则表达式、捕获与状态。
// 共同问题：全串匹配与搜索如何区分；捕获组如何读取；替换回调获得什么；
// 复用正则对象是否携带可变游标。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/cpp/language/test_013_literals_character_encodings_and_user_defined_literals.cpp

#include <gtest/gtest.h>

#include <regex>
#include <string>

namespace {

TEST(RegularExpressionsConcept, MatchAndSearchHaveDifferentAnchoring) {
  std::regex digits{"[0-9]+"};
  std::smatch match;
  std::string searched = "id=12";

  EXPECT_TRUE(std::regex_search(searched, match, digits));
  EXPECT_EQ(match.str(), "12");
  EXPECT_TRUE(std::regex_match(std::string{"12"}, digits));
  EXPECT_FALSE(std::regex_match(std::string{"id=12"}, digits));
}

TEST(RegularExpressionsConcept, CapturingGroupsAreNumbered) {
  std::regex pattern{"([a-z]+)-([0-9]+)"};
  std::smatch match;
  std::string input = "item-12";

  ASSERT_TRUE(std::regex_match(input, match, pattern));
  EXPECT_EQ(match[1].str(), "item");
  EXPECT_EQ(match[2].str(), "12");

  // ECMAScript grammar in std::regex does not provide JavaScript-style named capture API.
}

TEST(RegularExpressionsConcept, ReplaceUsesMatchReferencesInFormatString) {
  std::regex pattern{"([a-z]+)-([0-9]+)"};

  EXPECT_EQ(std::regex_replace(std::string{"item-12"}, pattern, "$2:$1"), "12:item");
}

TEST(RegularExpressionsConcept, RegexObjectDoesNotStoreASearchCursor) {
  std::regex pattern{"[0-9]"};

  EXPECT_TRUE(std::regex_search(std::string{"1"}, pattern));
  EXPECT_TRUE(std::regex_search(std::string{"1"}, pattern));
}

}  // namespace
