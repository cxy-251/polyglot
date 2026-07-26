// polyglot-covers:
// - cpp.stdlib.text.charconv-result-pointer-and-error-code
// - cpp.stdlib.text.to-chars-integer-base-buffer-and-no-terminator
// - cpp.stdlib.text.from-chars-integer-prefix-whitespace-and-partial-parse
// - cpp.stdlib.text.from-chars-invalid-and-out-of-range-value-preservation
// - cpp.stdlib.text.floating-charconv-format-precision-and-round-trip
// - cpp.stdlib.text.charconv-locale-independent-nonallocating-contract
// - cpp.stdlib.text.format-positional-fill-alignment-sign-and-dynamic-width
// - cpp.stdlib.text.format-to-format-to-n-and-formatted-size
// - cpp.stdlib.text.vformat-runtime-format-string-and-error
// - cpp.stdlib.text.locale-aware-formatting
// - cpp.stdlib.text.custom-formatter-parse-and-format-protocol
// - cpp.stdlib.text.locked-libstdcxx-format-gap

#include <gtest/gtest.h>

#include <array>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <iterator>
#include <limits>
#include <locale>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>

#if __has_include(<format>)
#include <format>
#endif

#if defined(__cpp_lib_format) && __cpp_lib_format >= 201907L
#define POLYGLOT_HAS_CXX20_FORMAT 1
#else
#define POLYGLOT_HAS_CXX20_FORMAT 0
#endif

namespace polyglot_examples {

struct Point {
  int x;
  int y;
};

}  // namespace polyglot_examples

#if POLYGLOT_HAS_CXX20_FORMAT
template <>
struct std::formatter<polyglot_examples::Point, char> {
  bool brackets = false;

  constexpr auto parse(std::format_parse_context& context) {
    auto current = context.begin();
    if (current != context.end() && *current == 'b') {
      brackets = true;
      ++current;
    }
    if (current != context.end() && *current != '}') {
      throw std::format_error{"Point only accepts the optional 'b' presentation"};
    }
    return current;
  }

  template <class FormatContext>
  auto format(const polyglot_examples::Point& point, FormatContext& context) const {
    if (brackets) {
      return std::format_to(context.out(), "[{}, {}]", point.x, point.y);
    }
    return std::format_to(context.out(), "({}, {})", point.x, point.y);
  }
};
#endif

namespace {

template <class Value>
concept DefaultToCharsCallable = requires(char* first, char* last, Value value) {
  std::to_chars(first, last, value);
};

TEST(ToCharsIntegers, ResultMarksTheWrittenHalfOpenRangeAndDoesNotAppendNull) {
  std::array<char, 16> buffer{};
  buffer.fill('?');

  const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), 255, 16);

  ASSERT_EQ(result.ec, std::errc{});
  EXPECT_EQ(std::string_view(buffer.data(), result.ptr), "ff");
  EXPECT_EQ(*result.ptr, '?');
  static_assert(!DefaultToCharsCallable<bool>);

  // 成功时 ptr 指向最后写入字符之后，区间 [first, ptr) 才是结果。to_chars 不追加
  // 零终止符，也不为 bool 提供整数重载；写 C 字符串时调用者必须另留一个字节。
}

TEST(ToCharsIntegers, BasesTwoThroughThirtySixUseLowercaseDigitsByDefault) {
  std::array<char, 64> buffer{};

  const auto binary = std::to_chars(buffer.data(), buffer.data() + buffer.size(), 42, 2);
  ASSERT_EQ(binary.ec, std::errc{});
  EXPECT_EQ(std::string_view(buffer.data(), binary.ptr), "101010");

  const auto base36 = std::to_chars(buffer.data(), buffer.data() + buffer.size(), 35, 36);
  ASSERT_EQ(base36.ec, std::errc{});
  EXPECT_EQ(std::string_view(buffer.data(), base36.ptr), "z");

  const auto negative = std::to_chars(buffer.data(), buffer.data() + buffer.size(), -42, 16);
  ASSERT_EQ(negative.ec, std::errc{});
  EXPECT_EQ(std::string_view(buffer.data(), negative.ptr), "-2a");

  // 整数格式没有 0x/0b 前缀、填充或大写选项；这些属于 format 或调用者拼装层。
}

TEST(ToCharsIntegers, InsufficientBufferReportsValueTooLargeWithoutAllocating) {
  std::array<char, 2> buffer{'?', '?'};

  const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), 1234);

  EXPECT_EQ(result.ec, std::errc::value_too_large);
  EXPECT_EQ(result.ptr, buffer.data() + buffer.size());

  // 失败后的字符内容未指定，不能依赖“完全没写”或截断文本。接口不分配、不抛出，
  // 调用者根据 ec 扩大缓冲区并重试。
}

TEST(FromCharsIntegers, ItParsesTheLongestPrefixWithoutSkippingWhitespaceOrPlus) {
  const std::string text{"42xyz"};
  int value = 0;
  const auto result = std::from_chars(text.data(), text.data() + text.size(), value);

  EXPECT_EQ(result.ec, std::errc{});
  EXPECT_EQ(value, 42);
  EXPECT_EQ(result.ptr, text.data() + 2);

  for (const std::string invalid : {" 42", "+42"}) {
    int unchanged = 7;
    const auto failure =
        std::from_chars(invalid.data(), invalid.data() + invalid.size(), unchanged);
    EXPECT_EQ(failure.ec, std::errc::invalid_argument);
    EXPECT_EQ(failure.ptr, invalid.data());
    EXPECT_EQ(unchanged, 7);
  }

  // 与 stoi 不同，from_chars 不跳过空白，整数正值也不接受 '+'，并用 ec 报错。
  // 这种严格、无 locale 语法适合协议解析，但完整字段仍要检查 ptr==last。
}

TEST(FromCharsIntegers, BaseIsExplicitAndCStylePrefixesAreNotConsumed) {
  const std::string prefixed{"0x2a"};
  int prefixed_value = -1;
  const auto prefixed_result = std::from_chars(
      prefixed.data(), prefixed.data() + prefixed.size(), prefixed_value, 16);

  EXPECT_EQ(prefixed_result.ec, std::errc{});
  EXPECT_EQ(prefixed_value, 0);
  EXPECT_EQ(prefixed_result.ptr, prefixed.data() + 1);

  const std::string plain{"-2a"};
  int plain_value = 0;
  const auto plain_result =
      std::from_chars(plain.data(), plain.data() + plain.size(), plain_value, 16);
  EXPECT_EQ(plain_result.ec, std::errc{});
  EXPECT_EQ(plain_value, -42);
  EXPECT_EQ(plain_result.ptr, plain.data() + plain.size());

  // base 没有 0 自动探测模式；即使 base=16，0x 也不属于数字表示，解析会在 x 前停下。
}

TEST(FromCharsIntegers, InvalidAndOutOfRangeConversionsLeaveTheDestinationUnchanged) {
  const std::string invalid{"no-number"};
  int invalid_value = 17;
  const auto invalid_result =
      std::from_chars(invalid.data(), invalid.data() + invalid.size(), invalid_value);

  EXPECT_EQ(invalid_result.ec, std::errc::invalid_argument);
  EXPECT_EQ(invalid_result.ptr, invalid.data());
  EXPECT_EQ(invalid_value, 17);

  const std::string huge{"999999999999999999999999999999999"};
  int range_value = 23;
  const auto range_result =
      std::from_chars(huge.data(), huge.data() + huge.size(), range_value);

  EXPECT_EQ(range_result.ec, std::errc::result_out_of_range);
  EXPECT_EQ(range_result.ptr, huge.data() + huge.size());
  EXPECT_EQ(range_value, 23);

  // ec 不是异常；忘记检查它会继续使用旧值，看起来像解析成功。ptr 仍指出本次扫描
  // 停止处，可用于诊断，但不能单凭“走到末尾”判断数值放得下。
}

TEST(FloatingCharconv, GeneralAndScientificFormatsExposeExactWrittenText) {
  std::array<char, 64> buffer{};

  const auto shortest = std::to_chars(
      buffer.data(), buffer.data() + buffer.size(), 1.25, std::chars_format::general);
  ASSERT_EQ(shortest.ec, std::errc{});
  EXPECT_EQ(std::string_view(buffer.data(), shortest.ptr), "1.25");

  const auto scientific = std::to_chars(
      buffer.data(), buffer.data() + buffer.size(), 12.5, std::chars_format::scientific, 2);
  ASSERT_EQ(scientific.ec, std::errc{});
  const std::string scientific_text{buffer.data(), scientific.ptr};
  EXPECT_NE(scientific_text.find('e'), std::string::npos);

  // 无 precision 的最短表示保证用相同 from_chars 精确回读；指定 precision 后则按
  // 格式进行舍入。不要把实现生成的指数位数写成跨标准库持久格式。
}

TEST(FloatingCharconv, ParsingHonorsTheRequestedGrammarAndReturnsTheSuffix) {
  const std::string text{"1.25e2ms"};
  double value = 0.0;
  const auto result = std::from_chars(
      text.data(), text.data() + text.size(), value, std::chars_format::general);

  EXPECT_EQ(result.ec, std::errc{});
  EXPECT_DOUBLE_EQ(value, 125.0);
  EXPECT_EQ(result.ptr, text.data() + 6);

  const std::string missing_exponent{"1.5"};
  double unchanged = 9.0;
  const auto scientific_only = std::from_chars(
      missing_exponent.data(),
      missing_exponent.data() + missing_exponent.size(),
      unchanged,
      std::chars_format::scientific);
  EXPECT_EQ(scientific_only.ec, std::errc::invalid_argument);
  EXPECT_DOUBLE_EQ(unchanged, 9.0);

  // scientific 单独使用时要求指数；general 才允许普通或科学记数法。
}

TEST(FloatingCharconv, HexGrammarOmitsTheCStylePrefix) {
  const std::string text{"1.8p+1"};
  double value = 0.0;
  const auto result = std::from_chars(
      text.data(), text.data() + text.size(), value, std::chars_format::hex);

  EXPECT_EQ(result.ec, std::errc{});
  EXPECT_DOUBLE_EQ(value, 3.0);
  EXPECT_EQ(result.ptr, text.data() + text.size());

  // from_chars 的十六进制浮点文法不接受 0x 前缀；加上前缀反而会先成功解析一个 0
  // 再停在 x。它与 strtod 的输入文法并不可以机械互换。
}

#if POLYGLOT_HAS_CXX20_FORMAT

TEST(Cxx20Format, FieldsControlPositionFillAlignmentSignBaseAndPrecision) {
  const auto text = std::format(
      "{1:0>4d} {0:+.2f} {2:#x} {3:*^7}", 3.14159, 7, 255, "ok");

  EXPECT_EQ(text, "0007 +3.14 0xff **ok***");
  EXPECT_EQ(std::format("{{{}}}", 42), "{42}");
  EXPECT_EQ(std::format("{:>{}}", "x", 4), "   x");

  // 字段索引可以重排参数；同一格式串不能混用自动和手工索引。宽度是最小宽度，
  // 精度对浮点控制有效数字/小数规则，对字符串则限制最大输出长度。
}

TEST(Cxx20Format, OutputIteratorOperationsSeparateWrittenPrefixFromRequiredSize) {
  std::string appended{"prefix:"};
  auto end = std::format_to(std::back_inserter(appended), "{}={}", "count", 3);
  *end = '!';
  EXPECT_EQ(appended, "prefix:count=3!");

  std::array<char, 5> buffer{};
  const auto limited = std::format_to_n(buffer.begin(), buffer.size(), "{}", "abcdef");
  EXPECT_EQ(std::string_view(buffer.data(), buffer.size()), "abcde");
  EXPECT_EQ(limited.out, buffer.end());
  EXPECT_EQ(limited.size, 6);
  EXPECT_EQ(std::formatted_size("{}={}", "count", 3), 7U);

  // format_to_n 最多写 n 个字符，但 size 是未截断的完整长度，可据此一次重新分配。
}

TEST(Cxx20Format, VformatAcceptsRuntimeTextAndReportsInvalidFormatAtRuntime) {
  const std::string runtime{"{} has {} items"};
  const std::string name{"box"};
  const int count = 4;

  EXPECT_EQ(
      std::vformat(runtime, std::make_format_args(name, count)),
      "box has 4 items");

  const std::string broken{"{"};
  EXPECT_THROW(
      std::vformat(broken, std::make_format_args(count)),
      std::format_error);

  // vformat 配合 make_format_args 处理运行期格式串；参数存储只引用实参，不能在实参
  // 生命周期结束后保存。无效格式通过 format_error 报告，不应吞掉后输出半成品。
}

TEST(Cxx20Format, LocaleIsUsedOnlyWhenExplicitlyRequestedByThePresentation) {
  const std::locale classic = std::locale::classic();

  EXPECT_EQ(std::format(classic, "{:L}", 1234567), "1234567");
  EXPECT_EQ(std::format(classic, "{}", 1234567), "1234567");

  // 传 locale 不代表所有字段自动本地化；数值需使用 L 选项。classic locale 没有
  // 分组，测试保持确定性；实际用户 locale 的分隔符由 num_put/numpunct 等 facet 决定。
}

TEST(Cxx20Format, CustomFormatterSeparatesSpecificationParsingFromValueFormatting) {
  const polyglot_examples::Point point{3, 4};

  EXPECT_EQ(std::format("{}", point), "(3, 4)");
  EXPECT_EQ(std::format("{:b}", point), "[3, 4]");

  const std::string invalid{"{:q}"};
  EXPECT_THROW(
      std::vformat(invalid, std::make_format_args(point)),
      std::format_error);

  // formatter::parse 只消费本类型的格式说明并返回 '}' 位置；format 把字符写入
  // context.out()。自定义 formatter 属于 std 中少数被标准明确允许的用户特化。
}

#else

TEST(Cxx20Format, LockedLibstdcxxGapPreservesTheCompleteFormattingUpgradePath) {
  GTEST_SKIP()
      << "GCC 11.4/libstdc++ 11.4 does not provide the C++20 <format> facility; "
         "the feature-gated branch keeps formatting, output iterators, locale, errors, "
         "and a custom formatter ready for a newer locked toolchain";
}

#endif

}  // namespace
