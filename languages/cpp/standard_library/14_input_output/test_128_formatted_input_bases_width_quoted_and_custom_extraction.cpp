// polyglot-covers:
// - cpp.stdlib.io.formatted-input-sentry-skipws-and-noskipws
// - cpp.stdlib.io.formatted-input-integer-base-and-setbase-zero
// - cpp.stdlib.io.formatted-input-boolalpha-and-noboolalpha
// - cpp.stdlib.io.formatted-input-width-string-and-character-array-boundary
// - cpp.stdlib.io.formatted-input-failure-value-and-recovery
// - cpp.stdlib.io.formatted-input-range-error-and-state
// - cpp.stdlib.io.quoted-input-delimiter-and-escape
// - cpp.stdlib.io.ws-manipulator-leading-whitespace-and-eof
// - cpp.stdlib.io.custom-extractor-sentry-temporary-and-failbit
// - cpp.stdlib.io.rvalue-stream-extraction-result

#include <gtest/gtest.h>

#include <iomanip>
#include <ios>
#include <limits>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>

namespace {

struct Point {
  int x = 0;
  int y = 0;

  friend bool operator==(const Point&, const Point&) = default;
};

std::istream& operator>>(std::istream& input, Point& point) {
  std::istream::sentry sentry{input};
  if (!sentry) {
    return input;
  }

  char opening = '\0';
  char comma = '\0';
  char closing = '\0';
  Point parsed;
  if (input.get(opening) && opening == '(' && input >> parsed.x &&
      input.get(comma) && comma == ',' && input >> parsed.y &&
      input.get(closing) && closing == ')') {
    point = parsed;
  } else {
    input.setstate(std::ios_base::failbit);
  }
  return input;
}

TEST(FormattedInputWhitespace, SkipwsIsDefaultAndNoskipwsExposesLeadingWhitespace) {
  std::istringstream default_input{"  42"};
  int value = 0;
  default_input >> value;
  EXPECT_EQ(value, 42);
  EXPECT_TRUE(default_input.eof());

  std::istringstream strict_input{" 42"};
  strict_input >> std::noskipws >> value;
  EXPECT_TRUE(strict_input.fail());

  strict_input.clear();
  char space = '\0';
  strict_input >> space;
  EXPECT_EQ(space, ' ');

  // 格式化输入的 sentry 默认按 locale 的 ctype 跳过空白；noskipws 关闭这一步。
  // char 的 operator>> 也是格式化输入，所以默认不会读取空格；逐字节读取用 get。
}

TEST(FormattedInputBases, SetbaseZeroRecognizesPrefixesWhileExplicitBasesPersist) {
  std::istringstream detected{"0xff 077 42"};
  int hexadecimal = 0;
  int octal = 0;
  int decimal = 0;
  detected >> std::setbase(0) >> hexadecimal >> octal >> decimal;

  EXPECT_EQ(hexadecimal, 255);
  EXPECT_EQ(octal, 63);
  EXPECT_EQ(decimal, 42);

  std::istringstream explicit_hex{"10 20"};
  int first = 0;
  int second = 0;
  explicit_hex >> std::hex >> first >> second;
  EXPECT_EQ(first, 16);
  EXPECT_EQ(second, 32);

  // setbase(0) 清 basefield，让 num_get 根据 0/0x 前缀探测；hex/dec/oct 则持续
  // 影响后续整数。协议通常应显式固定基数，避免用户的前导零意外变成八进制。
}

TEST(FormattedInputBooleans, BoolalphaSwitchesBetweenNamesAndIntegerSyntax) {
  std::istringstream words{"true false"};
  bool first = false;
  bool second = true;
  words >> std::boolalpha >> first >> second;
  EXPECT_TRUE(first);
  EXPECT_FALSE(second);

  std::istringstream digits{"1 0 2"};
  bool one = false;
  bool zero = true;
  bool invalid = false;
  digits >> std::noboolalpha >> one >> zero >> invalid;
  EXPECT_TRUE(one);
  EXPECT_FALSE(zero);
  EXPECT_TRUE(digits.fail());

  // noboolalpha 只接受能表示 bool 的整数值 0/1；2 会置 failbit。boolalpha 的
  // true/false 名称来自 locale 的 num_get，不应假定所有自定义 locale 都用英文。
}

TEST(FormattedInputWidth, StringWidthLimitsOneFieldThenAutomaticallyResets) {
  std::istringstream input{"abcdef rest"};
  std::string first;
  std::string second;

  input >> std::setw(4) >> first;
  EXPECT_EQ(first, "abcd");
  EXPECT_EQ(input.width(), 0);
  input >> second;
  EXPECT_EQ(second, "ef");

  // 对 string 提取，width 限制本次最多读取的字符数；成功后重置为 0。它不是
  // 持久字段宽度，也不包含随后留在流中的空白分隔符。
}

TEST(FormattedInputArrays, Cxx20ArrayOverloadUsesTheCompileTimeCapacity) {
  std::istringstream input{"abcdef"};
  char buffer[5]{};

  input >> buffer;

  EXPECT_STREQ(buffer, "abcd");
  EXPECT_EQ(input.peek(), 'e');

  // C++20 的字符数组重载知道 N，最多写 N-1 个字符并补零；退化成 char* 后就
  // 失去容量信息。新代码优先提取到 string，再做显式长度校验。
}

TEST(FormattedInputFailure, FailedArithmeticExtractionSetsAValueAndRequiresStateRecovery) {
  std::istringstream input{"10 bad 20"};
  int first = 0;
  int failed = 99;
  int last = 0;

  input >> first >> failed;
  EXPECT_EQ(first, 10);
  EXPECT_EQ(failed, 0);
  EXPECT_TRUE(input.fail());

  input.clear();
  std::string rejected_token;
  input >> rejected_token >> last;
  EXPECT_EQ(rejected_token, "bad");
  EXPECT_EQ(last, 20);

  // 算术提取完全无法转换时按标准写入零并置 failbit；状态未清前所有后续提取
  // 都立即失败。恢复要 clear 状态并消费导致失败的输入，否则会在同一位置循环。
}

TEST(FormattedInputRange, OutOfRangeArithmeticClampsAndSetsFailbit) {
  std::istringstream input{"999999"};
  short value = 0;

  input >> value;

  EXPECT_TRUE(input.fail());
  EXPECT_EQ(value, std::numeric_limits<short>::max());

  // num_get 得到的值超出目标整数范围时写入最近的上下界并置 failbit。即使变量
  // 看似有“合理数值”，状态仍表示输入无效，不能忽略 fail() 继续计算。
}

TEST(QuotedInput, ManipulatorConsumesQuotesEscapesAndCustomDelimiters) {
  std::istringstream input{R"("a \"quote\"" plain 'x\'y')"};
  std::string quoted_text;
  std::string plain;
  std::string custom;

  input >> std::quoted(quoted_text) >> std::quoted(plain) >>
      std::quoted(custom, '\'', '\\');

  EXPECT_EQ(quoted_text, "a \"quote\"");
  EXPECT_EQ(plain, "plain");
  EXPECT_EQ(custom, "x'y");

  // 开头不是 delimiter 时 quoted 退化成普通 string 提取；有引号时 escape 让下一
  // 字符按字面值进入结果。它适合简单字段，不等同于 JSON/CSV 的完整转义语法。
}

TEST(WsManipulator, ItConsumesLeadingWhitespaceAndCanEndWithEofWithoutFail) {
  std::istringstream input{" \t\n"};

  input >> std::ws;

  EXPECT_TRUE(input.eof());
  EXPECT_FALSE(input.fail());
  EXPECT_TRUE(static_cast<bool>(input));

  // ws 是一个显式的非字段空白消费器；读到 EOF 时只置 eofbit，不像 sentry 在
  // 一开始已处于 EOF 时还会置 failbit。常用于 getline 前清除一段剩余空白。
}

TEST(CustomExtractor, ParseIntoATemporarySoFailureDoesNotPartiallyModifyTheTarget) {
  Point point{9, 9};
  std::istringstream valid{"  (3, 4)"};
  valid >> point;
  EXPECT_EQ(point, (Point{3, 4}));
  EXPECT_TRUE(valid.good());

  std::istringstream invalid{"(7;x)"};
  invalid >> point;
  EXPECT_TRUE(invalid.fail());
  EXPECT_EQ(point, (Point{3, 4}));

  // 自定义提取先建立 sentry，再把所有字段读入临时值；只有完整语法成功才提交。
  // 失败时设置 failbit 并保留原对象，提供类似事务的基本异常/错误保证。
}

TEST(RvalueStreamExtraction, TemporaryStringStreamCanFeedAValueAndReturnAsAStreamReference) {
  int value = 0;
  const bool reached_eof = (std::istringstream{"42"} >> value).eof();
  using Result = decltype(std::declval<std::istringstream>() >> std::declval<int&>());

  static_assert(std::is_same_v<Result, std::istringstream&&>);
  EXPECT_EQ(value, 42);
  EXPECT_TRUE(reached_eof);

  // rvalue 流重载支持临时流链式解析，并保持具体派生流的右值类型。把该引用保存
  // 超过完整表达式不会延长临时对象寿命，因此示例只在同一表达式读取状态。
}

}  // namespace
