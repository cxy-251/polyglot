// polyglot-covers:
// - cpp.stdlib.localization.time-put-pattern-literals-directives-and-output-iterator
// - cpp.stdlib.localization.put-time-stream-manipulator-and-locale-facet
// - cpp.stdlib.localization.time-put-custom-do-put-per-directive-dispatch
// - cpp.stdlib.localization.time-get-format-range-whitespace-and-iostate
// - cpp.stdlib.localization.get-time-stream-manipulator-and-zeroed-tm
// - cpp.stdlib.localization.time-get-weekday-month-year-incremental-members
// - cpp.stdlib.localization.time-get-date-order-and-implementation-defined-parsing
// - cpp.stdlib.localization.time-get-failure-and-unspecified-tm-fields
// - cpp.stdlib.localization.time-get-put-byname-c-facets

#include <gtest/gtest.h>

#include <ctime>
#include <iomanip>
#include <ios>
#include <iterator>
#include <locale>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

std::tm leap_day() {
  std::tm value{};
  value.tm_sec = 5;
  value.tm_min = 7;
  value.tm_hour = 23;
  value.tm_mday = 29;
  value.tm_mon = 1;
  value.tm_year = 124;
  value.tm_wday = 4;
  value.tm_yday = 59;
  value.tm_isdst = 0;
  return value;
}

class RecordingTimePut : public std::time_put<char> {
 public:
  using Call = std::pair<char, char>;

  [[nodiscard]] const std::vector<Call>& calls() const noexcept { return calls_; }

 protected:
  iter_type do_put(
      iter_type output,
      std::ios_base&,
      char,
      const std::tm*,
      char format,
      char modifier) const override {
    calls_.emplace_back(format, modifier);
    *output++ = '<';
    if (modifier != '\0') {
      *output++ = modifier;
    }
    *output++ = format;
    *output++ = '>';
    return output;
  }

 private:
  mutable std::vector<Call> calls_;
};

TEST(TimePutFacet, PatternOverloadInterleavesLiteralsAndLocalizedDirectives) {
  const std::tm value = leap_day();
  std::ostringstream output;
  output.imbue(std::locale::classic());
  const auto& facet = std::use_facet<std::time_put<char>>(output.getloc());
  const std::string pattern = "%Y-%m-%d %H:%M:%S %a %b";

  const auto end = facet.put(
      std::ostreambuf_iterator<char>{output},
      output,
      ' ',
      &value,
      pattern.data(),
      pattern.data() + pattern.size());

  EXPECT_FALSE(end.failed());
  EXPECT_EQ(output.str(), "2024-02-29 23:07:05 Thu Feb");

  // pattern 重载原样写普通字符，每遇到 % 指令调用 do_put；输出迭代器指向结果
  // 末端并可报告失败。tm_year 从 1900 起、tm_mon 从 0 起，是最常见的偏移陷阱。
}

TEST(PutTimeManipulator, StreamLocaleSelectsTheFacetButNotATimeZone) {
  const std::tm value = leap_day();
  std::ostringstream output;
  output.imbue(std::locale::classic());

  output << std::put_time(&value, "%F %T");

  EXPECT_EQ(output.str(), "2024-02-29 23:07:05");

  // put_time 只是把 tm 与格式交给流的 time_put facet；它不会做时区转换，也不会
  // 校验这些字段是否共同组成真实日期。时区/历法转换应先由 chrono 或业务层完成。
}

TEST(TimePutCustomization, EachDirectiveDispatchesSeparatelyToDoPut) {
  const std::tm value = leap_day();
  const std::locale locale{
      std::locale::classic(),
      new RecordingTimePut};
  std::ostringstream output;
  output.imbue(locale);

  output << std::put_time(&value, "date=%Y/%m");

  EXPECT_EQ(output.str(), "date=<Y>/<m>");
  const auto& recording =
      static_cast<const RecordingTimePut&>(
          std::use_facet<std::time_put<char>>(locale));
  EXPECT_EQ(
      recording.calls(),
      (std::vector<RecordingTimePut::Call>{{'Y', '\0'}, {'m', '\0'}}));

  // 派生 facet 的 do_put 一次接收一个 specifier，而不是完整格式串；若多个字段
  // 需要共同上下文，必须在 facet 内显式管理，同时保持 const 调用的并发安全。
}

TEST(GetTimeManipulator, AZeroedTmReceivesParsedFieldsWithoutMktimeRoundTrip) {
  std::istringstream input{"2024-02-29 23:07:05"};
  input.imbue(std::locale::classic());
  std::tm parsed{};

  input >> std::get_time(&parsed, "%Y-%m-%d %H:%M:%S");

  EXPECT_FALSE(input.fail());
  EXPECT_EQ(parsed.tm_year, 124);
  EXPECT_EQ(parsed.tm_mon, 1);
  EXPECT_EQ(parsed.tm_mday, 29);
  EXPECT_EQ(parsed.tm_hour, 23);
  EXPECT_EQ(parsed.tm_min, 7);
  EXPECT_EQ(parsed.tm_sec, 5);
  EXPECT_GE(parsed.tm_wday, 0);
  EXPECT_LE(parsed.tm_wday, 6);

  // 标准保证写入格式对应字段，但没有保证其余字段保持旧值；实现可顺带推导星期。
  // 多次写同一 tm 是覆盖还是增量更新也未指定，因此每次解析前应把整个对象清零。
}

TEST(TimeGetPattern, FormatWhitespaceConsumesAnyAmountOfInputWhitespace) {
  using Iterator = std::istreambuf_iterator<char>;
  std::istringstream input{"2024\t  February   29tail"};
  input.imbue(std::locale::classic());
  const auto& facet = std::use_facet<std::time_get<char>>(input.getloc());
  const std::string pattern = "%Y %B %d";
  std::ios_base::iostate state = std::ios_base::goodbit;
  std::tm parsed{};

  const Iterator next = facet.get(
      Iterator{input},
      Iterator{},
      input,
      state,
      &parsed,
      pattern.data(),
      pattern.data() + pattern.size());

  EXPECT_EQ(state, std::ios_base::goodbit);
  EXPECT_EQ(parsed.tm_year, 124);
  EXPECT_EQ(parsed.tm_mon, 1);
  EXPECT_EQ(parsed.tm_mday, 29);
  ASSERT_NE(next, Iterator{});
  EXPECT_EQ(*next, 't');

  // 格式串中的一段 locale 空白匹配输入中的零个或多个空白；普通字符则进行实现
  // 规定的大小写无关匹配。返回迭代器保留未消费尾缀，便于组合更大的语法。
}

TEST(TimeGetMembers, WeekdayMonthAndYearCanBeParsedIncrementally) {
  using Iterator = std::istreambuf_iterator<char>;
  std::istringstream input{"Thursday February 2024"};
  input.imbue(std::locale::classic());
  const auto& facet = std::use_facet<std::time_get<char>>(input.getloc());
  Iterator next{input};
  const Iterator end{};
  std::ios_base::iostate state = std::ios_base::goodbit;
  std::tm parsed{};

  next = facet.get_weekday(next, end, input, state, &parsed);
  ASSERT_EQ(state, std::ios_base::goodbit);
  ASSERT_NE(next, end);
  ASSERT_EQ(*next, ' ');
  ++next;
  next = facet.get_monthname(next, end, input, state, &parsed);
  ASSERT_EQ(state, std::ios_base::goodbit);
  ASSERT_NE(next, end);
  ASSERT_EQ(*next, ' ');
  ++next;
  next = facet.get_year(next, end, input, state, &parsed);

  EXPECT_EQ(parsed.tm_wday, 4);
  EXPECT_EQ(parsed.tm_mon, 1);
  EXPECT_EQ(parsed.tm_year, 124);
  EXPECT_EQ(next, end);
  EXPECT_NE(state & std::ios_base::eofbit, 0);

  // 名称解析会在缩写仍可能扩展为全名时继续读取；调用者负责处理成员之间的分隔
  // 符。两位年份是否接受及落入哪个世纪由实现定义，机器协议应使用完整年份。
}

TEST(TimeGetMetadata, DateOrderIsOnlyAHintAndFailureMakesParsedFieldsUnreliable) {
  const auto& facet =
      std::use_facet<std::time_get<char>>(std::locale::classic());
  const auto order = facet.date_order();
  EXPECT_TRUE(
      order == std::time_base::no_order ||
      order == std::time_base::dmy ||
      order == std::time_base::mdy ||
      order == std::time_base::ymd ||
      order == std::time_base::ydm);

  std::istringstream invalid{"2024-not-a-month-29"};
  invalid.imbue(std::locale::classic());
  std::tm parsed{};
  invalid >> std::get_time(&parsed, "%Y-%m-%d");
  EXPECT_TRUE(invalid.fail());

  // date_order 对合法 locale 也可返回 no_order，只适合界面提示。解析失败后部分
  // tm 字段可能已写入甚至为未指定值；检查 failbit 后应丢弃整个结果而非修补复用。
}

TEST(TimeFacetsByName, NamedCFacetsCanBeComposedForExplicitDeploymentPolicy) {
  std::locale named{
      std::locale::classic(),
      new std::time_get_byname<char>{"C"}};
  named = std::locale{named, new std::time_put_byname<char>{"C"}};
  std::ostringstream output;
  output.imbue(named);
  const std::tm value = leap_day();

  output << std::put_time(&value, "%a %b");
  EXPECT_EQ(output.str(), "Thu Feb");

  // 同一 locale 名可分别安装 time_get/time_put；除 C 外的有效名称和具体文本来自
  // 系统数据库。不要用当前进程 locale 隐式决定持久化日期格式。
}

}  // namespace
