// polyglot-covers:
// - cpp.stdlib.regex.construction-grammar-flags-mark-count-and-nosubs
// - cpp.stdlib.regex.regex-error-code-and-invalid-expression
// - cpp.stdlib.regex.match-whole-input-versus-search-subsequence
// - cpp.stdlib.regex.match-results-captures-prefix-suffix-position-and-format
// - cpp.stdlib.regex.unmatched-subexpression-state
// - cpp.stdlib.regex.match-flags-bol-continuous-and-nonempty
// - cpp.stdlib.regex.deleted-rvalue-string-algorithm-overloads
// - cpp.stdlib.regex.replace-copy-first-only-no-copy-and-sed-format
// - cpp.stdlib.regex.regex-iterator-match-sequence
// - cpp.stdlib.regex.regex-token-iterator-captures-and-gaps
// - cpp.stdlib.regex.regex-traits-character-class-value-and-translation
// - cpp.stdlib.regex.multiline-anchors-and-raw-string-patterns
// - cpp.stdlib.regex.backtracking-performance-and-lifetime-traps

#include <gtest/gtest.h>

#include <algorithm>
#include <iterator>
#include <locale>
#include <regex>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <class Text>
concept RegexSearchWithResults =
    requires(Text&& text, std::smatch& match, const std::regex& expression) {
      std::regex_search(std::forward<Text>(text), match, expression);
};

TEST(RegexConstruction, GrammarAndOptionsBecomePartOfTheCompiledExpression) {
  const std::regex expression{
      R"((name)=(\w+))",
      std::regex_constants::ECMAScript | std::regex_constants::icase};

  EXPECT_EQ(expression.mark_count(), 2U);
  EXPECT_NE(expression.flags() & std::regex_constants::icase, std::regex::flag_type{});
  EXPECT_TRUE(std::regex_match("NAME=Alice", expression));

  const std::regex no_captures{
      R"((name)=(\w+))",
      std::regex_constants::ECMAScript | std::regex_constants::nosubs};
  EXPECT_EQ(no_captures.mark_count(), 0U);
  EXPECT_TRUE(std::regex_match("name=Alice", no_captures));

  // nosubs 只关闭子表达式报告，不改变是否匹配。ECMAScript 是默认文法；basic、
  // extended、awk、grep、egrep 的转义和量词规则不同，不能混用教程中的模式。
}

TEST(RegexConstruction, InvalidPatternThrowsRegexErrorWithAClassifiedCode) {
  try {
    const std::regex invalid{"("};
    (void)invalid;
    FAIL() << "an unmatched parenthesis must be rejected";
  } catch (const std::regex_error& error) {
    EXPECT_EQ(error.code(), std::regex_constants::error_paren);
    EXPECT_NE(std::string{error.what()}.size(), 0U);
  }

  // regex_error::code 比 what() 文本稳定，后者由实现决定。模式来自用户时应在配置
  // 边界捕获异常，而不是让一次坏表达式终止整个搜索流程。
}

TEST(RegexAlgorithms, MatchRequiresTheWholeSequenceWhileSearchFindsASubsequence) {
  const std::string input{"id=42;"};
  const std::regex assignment{R"((\w+)=(\d+))"};

  EXPECT_FALSE(std::regex_match(input, assignment));
  EXPECT_TRUE(std::regex_search(input, assignment));
  EXPECT_TRUE(std::regex_match(input, std::regex{R"((\w+)=(\d+);)"}));

  // regex_match 隐含“从头到尾”要求；regex_search 才是在任意位置寻找一次匹配。
  // 不要为了整串校验随手用 search，否则合法前缀后面的垃圾会被忽略。
}

TEST(MatchResults, CapturesPrefixSuffixPositionsAndFormattingReferenceTheOriginalText) {
  const std::string input{"id=42; next"};
  const std::regex assignment{R"((\w+)=(\d+))"};
  std::smatch match;

  EXPECT_FALSE(match.ready());
  ASSERT_TRUE(std::regex_search(input, match, assignment));
  EXPECT_TRUE(match.ready());
  ASSERT_EQ(match.size(), 3U);
  EXPECT_EQ(match.str(0), "id=42");
  EXPECT_EQ(match[1].str(), "id");
  EXPECT_EQ(match[2].str(), "42");
  EXPECT_EQ(match.prefix().str(), "");
  EXPECT_EQ(match.suffix().str(), "; next");
  EXPECT_EQ(match.position(2), 3);
  EXPECT_EQ(match.length(0), 5);
  EXPECT_EQ(match.format("$2/$1"), "42/id");

  // sub_match 与 prefix/suffix 保存的是原输入迭代器，不拥有字符。input 被销毁或
  // 发生使迭代器失效的修改后，match_results 中的访问也会悬空。
}

TEST(MatchResults, AnOptionalGroupCanExistInThePatternWithoutParticipating) {
  const std::string input{"b"};
  const std::regex expression{R"((a)?(b))"};
  std::smatch match;

  ASSERT_TRUE(std::regex_match(input, match, expression));
  ASSERT_EQ(match.size(), 3U);
  EXPECT_FALSE(match[1].matched);
  EXPECT_TRUE(match[1].str().empty());
  EXPECT_TRUE(match[2].matched);
  EXPECT_EQ(match[2].str(), "b");

  // “未参与捕获”和“成功捕获空字符串”都可能得到空 str()，需要检查 matched 区分。
}

TEST(RegexMatchFlags, CallSiteCanChangeAnchorsContinuityAndEmptyMatchAcceptance) {
  const std::regex anchored{"^abc"};
  EXPECT_TRUE(std::regex_search("abc", anchored));
  EXPECT_FALSE(std::regex_search("abc", anchored, std::regex_constants::match_not_bol));

  const std::regex plain{"abc"};
  EXPECT_TRUE(std::regex_search("xabc", plain));
  EXPECT_FALSE(
      std::regex_search("xabc", plain, std::regex_constants::match_continuous));

  const std::regex empty_allowed{"a*"};
  EXPECT_TRUE(std::regex_search("bbb", empty_allowed));
  EXPECT_FALSE(
      std::regex_search("bbb", empty_allowed, std::regex_constants::match_not_null));

  // match_continuous 要求匹配从传入范围首位置开始；match_not_null 拒绝空匹配，
  // 可避免把“找到长度为零”误判为有意义令牌。
}

TEST(RegexAlgorithmLifetime, RvalueStringOverloadsAreDeletedToPreventImmediateDangling) {
  static_assert(RegexSearchWithResults<std::string&>);
  static_assert(RegexSearchWithResults<const std::string&>);
  static_assert(!RegexSearchWithResults<std::string>);

  const std::string input{"abc123"};
  std::smatch match;
  ASSERT_TRUE(std::regex_search(input, match, std::regex{R"(\d+)"}));
  EXPECT_EQ(match.str(), "123");

  // 接收 match_results 的 string 右值重载被删除，因为结果会立即引用已销毁的临时
  // 字符串。先保存 owning string，或改用迭代器并保证底层存储寿命。
}

TEST(RegexReplace, DefaultModeCopiesUnmatchedTextAndCanReorderCaptures) {
  const std::string input{"Ada Lovelace; Alan Turing"};
  const std::regex person{R"((\w+)\s+(\w+))"};

  EXPECT_EQ(
      std::regex_replace(input, person, "$2, $1"),
      "Lovelace, Ada; Turing, Alan");
  EXPECT_EQ(
      std::regex_replace(
          input,
          person,
          "$2, $1",
          std::regex_constants::format_first_only),
      "Lovelace, Ada; Alan Turing");

  // 默认替换所有不重叠匹配，并原样复制匹配之间的文本；first_only 只替换首个。
}

TEST(RegexReplace, NoCopyAndSedFlagsChangeTheReplacementLanguageAndOutput) {
  const std::string input{"Ada Lovelace; Alan Turing"};
  const std::regex person{R"((\w+)\s+(\w+))"};

  EXPECT_EQ(
      std::regex_replace(
          input,
          person,
          "$2, $1",
          std::regex_constants::format_no_copy),
      "Lovelace, AdaTuring, Alan");
  EXPECT_EQ(
      std::regex_replace(
          input,
          person,
          R"(\2, \1)",
          std::regex_constants::format_sed),
      "Lovelace, Ada; Turing, Alan");

  std::string output{"people:"};
  std::regex_replace(
      std::back_inserter(output), input.begin(), input.end(), person, "<$1>");
  EXPECT_EQ(output, "people:<Ada>; <Alan>");

  // format_no_copy 丢弃所有未匹配片段；format_sed 用 \1 而非 $1 引用捕获。
  // 输出迭代器重载直接追加到目标，不会自动清空已有内容。
}

TEST(RegexIterator, ItEnumeratesSuccessiveNonOverlappingMatchesWithPositions) {
  const std::string input{"id=7, count=42, zero=0"};
  const std::regex number{R"(\d+)"};
  std::vector<std::string> values;
  std::vector<std::ptrdiff_t> positions;

  for (std::sregex_iterator current{input.begin(), input.end(), number}, end;
       current != end;
       ++current) {
    values.push_back(current->str());
    positions.push_back(current->position());
  }

  EXPECT_EQ(values, (std::vector<std::string>{"7", "42", "0"}));
  EXPECT_EQ(positions, (std::vector<std::ptrdiff_t>{3, 12, 21}));

  // regex_iterator 是只读前向迭代器，每一步保存当前 match_results。它与输入和
  // regex 都存在寿命关系，遍历期间不要修改输入或替换表达式对象。
}

TEST(RegexTokenIterator, SelectedCaptureIndicesFlattenEachMatchInTheGivenOrder) {
  const std::string input{"name=alice id=42"};
  const std::regex assignment{R"((\w+)=(\w+))"};
  const std::vector<int> groups{1, 2};
  std::vector<std::string> tokens;

  for (std::sregex_token_iterator current{
           input.begin(), input.end(), assignment, groups};
       current != std::sregex_token_iterator{};
       ++current) {
    tokens.push_back(current->str());
  }

  EXPECT_EQ(tokens, (std::vector<std::string>{"name", "alice", "id", "42"}));

  // 多个 submatch 索引按每次匹配依次展开；索引 0 是整段，正数是捕获组，-1
  // 表示上次匹配与本次匹配之间未匹配的片段。
}

TEST(RegexTokenIterator, MinusOneTurnsDelimiterMatchesIntoAViewLikeSplit) {
  const std::string input{"alpha,,beta;gamma"};
  const std::regex delimiter{"[,;]"};
  std::vector<std::string> fields;

  for (std::sregex_token_iterator current{
           input.begin(), input.end(), delimiter, -1};
       current != std::sregex_token_iterator{};
       ++current) {
    fields.push_back(current->str());
  }

  EXPECT_EQ(fields, (std::vector<std::string>{"alpha", "", "beta", "gamma"}));

  // 与 strtok 不同，相邻分隔符产生空字段且不修改输入；结果仍是指向 input 的
  // sub_match，不是拥有型 string，示例复制后再长期保存。
}

TEST(RegexTraits, ItProvidesLocaleAwareCharacterTranslationClassesAndDigitValues) {
  std::regex_traits<char> traits;
  traits.imbue(std::locale::classic());

  EXPECT_EQ(traits.length("abc"), 3U);
  EXPECT_EQ(traits.translate('A'), 'A');
  EXPECT_EQ(traits.translate_nocase('A'), 'a');
  EXPECT_EQ(traits.value('f', 16), 15);
  EXPECT_EQ(traits.value('z', 16), -1);

  const auto alpha = traits.lookup_classname("alpha", "alpha" + 5);
  EXPECT_TRUE(traits.isctype('A', alpha));
  EXPECT_FALSE(traits.isctype('7', alpha));

  // regex_traits 是文法引擎与字符/locale 的协议层。自定义 traits 很少必要，
  // 但它解释了 icase、字符类和 collate 为什么可能随 locale 改变。
}

TEST(RegexAnchors, MultilineLetsLineBoundariesSatisfyAnchorsInEcmaScriptGrammar) {
  const std::string input{"header\nitem=42\nfooter"};
  const std::regex single_line{R"(^item=(\d+)$)"};
  const std::regex multiline{
      R"(^item=(\d+)$)",
      std::regex_constants::ECMAScript | std::regex_constants::multiline};
  std::smatch match;

  EXPECT_FALSE(std::regex_search(input, match, single_line));
  ASSERT_TRUE(std::regex_search(input, match, multiline));
  EXPECT_EQ(match[1].str(), "42");

  // raw string 避免 C++ 字面量层再次转义反斜杠；multiline 让 ^/$ 识别行边界，
  // 但它不等于“点号匹配换行”。复杂或不可信模式还要防范灾难性回溯造成拒绝服务。
}

}  // namespace
