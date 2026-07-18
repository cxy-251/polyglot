// polyglot-covers:
// - cpp.stdlib.localization.numpunct-decimal-thousands-grouping-and-bool-names
// - cpp.stdlib.localization.numpunct-byname-c-facet
// - cpp.stdlib.localization.num-put-stream-flags-fill-and-locale-punctuation
// - cpp.stdlib.localization.num-get-staged-parsing-iterator-and-iostate-protocol
// - cpp.stdlib.localization.numeric-formatted-stream-facet-workflow
// - cpp.stdlib.localization.numeric-grouping-validation-failbit
// - cpp.stdlib.localization.numeric-base-autodetection-and-pointer-roundtrip
// - cpp.stdlib.localization.numeric-overflow-saturation-and-failbit
// - cpp.stdlib.localization.boolalpha-locale-names-and-exact-matching

#include <gtest/gtest.h>

#include <iomanip>
#include <ios>
#include <iterator>
#include <limits>
#include <locale>
#include <sstream>
#include <string>

namespace {

class TeachingNumpunct : public std::numpunct<char> {
 protected:
  char do_decimal_point() const override { return ','; }
  char do_thousands_sep() const override { return '_'; }
  std::string do_grouping() const override { return "\3"; }
  std::string do_truename() const override { return "yes"; }
  std::string do_falsename() const override { return "no"; }
};

std::locale teaching_numeric_locale() {
  return {std::locale::classic(), new TeachingNumpunct};
}

TEST(NumpunctFacet, CustomPunctuationIsDataConsumedByOtherNumericFacets) {
  const std::locale locale = teaching_numeric_locale();
  const auto& punctuation = std::use_facet<std::numpunct<char>>(locale);

  EXPECT_EQ(punctuation.decimal_point(), ',');
  EXPECT_EQ(punctuation.thousands_sep(), '_');
  EXPECT_EQ(punctuation.grouping(), std::string(1, '\3'));
  EXPECT_EQ(punctuation.truename(), "yes");
  EXPECT_EQ(punctuation.falsename(), "no");

  // grouping 的每个字节是从最右侧开始的组宽，不是文本数字 "3"；CHAR_MAX 表示
  // 不再分组，0 表示重复上一宽度。numpunct 只给规则，num_get/num_put 执行规则。
}

TEST(NumpunctByName, NamedCFacetCanBeComposedWithoutDependingOnExtraLocales) {
  const std::locale named{
      std::locale::classic(),
      new std::numpunct_byname<char>{"C"}};
  const auto& punctuation = std::use_facet<std::numpunct<char>>(named);

  EXPECT_EQ(punctuation.decimal_point(), '.');
  EXPECT_TRUE(punctuation.grouping().empty());
  EXPECT_EQ(punctuation.truename(), "true");
  EXPECT_EQ(punctuation.falsename(), "false");

  // byname 依赖实现的 locale 数据库；标准只保证 "C" 可用。测试或服务若直接假设
  // en_US.UTF-8 一定安装，会把部署差异误判成语法/业务错误。
}

TEST(NumericStreams, ImbuedLocaleDrivesBoolIntegerAndFloatingFormattingTogether) {
  std::ostringstream output;
  output.imbue(teaching_numeric_locale());
  output << std::boolalpha << true << ' ' << std::showpos << 1234567 << ' '
         << std::fixed << std::setprecision(2) << 1234.5;

  EXPECT_EQ(output.str(), "yes +1_234_567 +1_234,50");

  std::istringstream input{output.str()};
  input.imbue(teaching_numeric_locale());
  bool boolean = false;
  int integer = 0;
  double floating = 0.0;
  input >> std::boolalpha >> boolean >> integer >> floating;

  EXPECT_TRUE(boolean);
  EXPECT_EQ(integer, 1234567);
  EXPECT_DOUBLE_EQ(floating, 1234.5);
  EXPECT_FALSE(input.fail());

  // 同一个 locale 会影响 bool 名称、分组和小数点；序列化协议必须同时锁定 locale
  // 与格式 flags。只在写端 imbue 会让读端把逗号当终止符，而不是小数点。
}

TEST(NumPutFacet, DirectPutUsesTheOwningStreamForFlagsLocaleAndFill) {
  using Iterator = std::ostreambuf_iterator<char>;
  std::ostringstream output;
  output.imbue(teaching_numeric_locale());
  output.setf(std::ios_base::showpos);
  output.width(12);
  output.setf(std::ios_base::internal, std::ios_base::adjustfield);
  const auto& facet = std::use_facet<std::num_put<char>>(output.getloc());

  const Iterator end = facet.put(Iterator{output}, output, '.', 1234567L);

  EXPECT_FALSE(end.failed());
  EXPECT_EQ(output.str(), "+..1_234_567");
  EXPECT_EQ(output.width(), 0);

  // num_put 从 ios_base 读取 flags、width 和 locale，并接收单独 fill 字符；和
  // operator<< 一样，width 只消费一次后归零。返回输出迭代器可报告写入失败。
}

TEST(NumGetFacet, DirectGetReturnsTheStopIteratorAndAccumulatesIoState) {
  using Iterator = std::istreambuf_iterator<char>;
  std::istringstream input{"1_234,5tail"};
  input.imbue(teaching_numeric_locale());
  const auto& facet = std::use_facet<std::num_get<char>>(input.getloc());
  std::ios_base::iostate state = std::ios_base::goodbit;
  double value = 0.0;

  const Iterator next = facet.get(
      Iterator{input},
      Iterator{},
      input,
      state,
      value);

  EXPECT_DOUBLE_EQ(value, 1234.5);
  EXPECT_EQ(state, std::ios_base::goodbit);
  ASSERT_NE(next, Iterator{});
  EXPECT_EQ(*next, 't');

  // num_get 分阶段收集可接受字符、转换并校验分组；它不负责 formatted input
  // sentry 的前导空白处理。返回迭代器指出未消费尾缀，state 可能同时含 eofbit/failbit。
}

TEST(NumericGrouping, WrongSeparatorPlacementSetsFailbitEvenWhenDigitsAreUsable) {
  std::istringstream input{"12_34"};
  input.imbue(teaching_numeric_locale());
  long value = -1;

  input >> value;

  EXPECT_TRUE(input.fail());
  EXPECT_EQ(value, 1234L);

  // 分隔符会在转换前从数字序列中移除，但实际组宽仍须匹配 grouping；因此可能
  // 同时得到数值和 failbit。生产代码不能只检查目标变量是否“看起来正确”。
}

TEST(NumericBases, SetbaseZeroRecognizesPrefixesAndPointersHaveTheirOwnOverload) {
  std::istringstream numbers{"0x2a 075 42"};
  int hexadecimal = 0;
  int octal = 0;
  int decimal = 0;
  numbers >> std::setbase(0) >> hexadecimal >> octal >> decimal;

  EXPECT_EQ(hexadecimal, 42);
  EXPECT_EQ(octal, 61);
  EXPECT_EQ(decimal, 42);

  int object = 7;
  std::ostringstream pointer_text;
  pointer_text << static_cast<void*>(&object);
  std::istringstream pointer_input{pointer_text.str()};
  void* restored = nullptr;
  pointer_input >> restored;
  EXPECT_EQ(restored, static_cast<void*>(&object));

  // setbase(0) 在输入端启用 C 风格前缀探测；默认 dec 不会。void* 使用独立的
  // num_put/num_get 重载，文本形式由实现选择，只应由同类格式器解析而非手工切片。
}

TEST(NumericRangeErrors, OverflowSaturatesTheDestinationAndSetsFailbit) {
  std::istringstream positive{"999999999999999999999999999999"};
  long positive_value = 0;
  positive >> positive_value;
  EXPECT_TRUE(positive.fail());
  EXPECT_EQ(positive_value, std::numeric_limits<long>::max());

  std::istringstream negative{"-999999999999999999999999999999"};
  long negative_value = 0;
  negative >> negative_value;
  EXPECT_TRUE(negative.fail());
  EXPECT_EQ(negative_value, std::numeric_limits<long>::min());

  // num_get 对目标整数越界写入相应端点并置 failbit；旧值不会保留。要区分合法的
  // LONG_MAX/MIN 与饱和错误，必须在读取后检查流状态。
}

TEST(BoolalphaParsing, LocalizedNamesMustMatchAndIncompleteInputFails) {
  std::istringstream valid{"yes no"};
  valid.imbue(teaching_numeric_locale());
  bool first = false;
  bool second = true;
  valid >> std::boolalpha >> first >> second;
  EXPECT_TRUE(first);
  EXPECT_FALSE(second);
  EXPECT_FALSE(valid.fail());

  std::istringstream incomplete{"ye"};
  incomplete.imbue(teaching_numeric_locale());
  bool value = true;
  incomplete >> std::boolalpha >> value;
  EXPECT_TRUE(incomplete.fail());
  EXPECT_TRUE(incomplete.eof());

  // boolalpha 匹配 numpunct 提供的完整名称，不接受任意前缀；名称若共享前缀，
  // num_get 会继续读取到能消歧或失败，交互式协议要考虑这类阻塞边界。
}

}  // namespace
