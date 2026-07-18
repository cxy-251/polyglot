// polyglot-covers:
// - cpp.stdlib.localization.ctype-mask-classification-scan-and-range-operations
// - cpp.stdlib.localization.ctype-widen-narrow-and-case-conversion
// - cpp.stdlib.localization.ctype-custom-table-and-virtual-case-mapping
// - cpp.stdlib.localization.ctype-byname-c-locale
// - cpp.stdlib.localization.locale-character-convenience-function-facet-dispatch
// - cpp.stdlib.localization.locale-unsigned-char-convenience-overload-bad-cast-trap
// - cpp.stdlib.localization.codecvt-char-no-conversion-specialization
// - cpp.stdlib.localization.codecvt-length-and-unshift-protocol
// - cpp.stdlib.localization.codecvt-wide-multibyte-state-and-pointer-protocol
// - cpp.stdlib.localization.codecvt-byname-c-locale
// - cpp.stdlib.localization.codecvt-utf8-utf16-ok-partial-and-error-results
// - cpp.stdlib.localization.codecvt-deprecation-and-code-unit-boundaries

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <codecvt>
#include <cstddef>
#include <cwchar>
#include <locale>
#include <string>

namespace {

class TeachingCtype : public std::ctype<char> {
 public:
  TeachingCtype() : std::ctype<char>{teaching_table()} {}

 private:
  static const mask* teaching_table() {
    static const std::array<mask, table_size> table = [] {
      std::array<mask, table_size> result{};
      std::copy_n(classic_table(), table_size, result.begin());
      result[static_cast<unsigned char>('@')] |= alpha;
      return result;
    }();
    return table.data();
  }

  char do_toupper(char value) const override {
    if (value == 'a') {
      return '4';
    }
    return std::ctype<char>::do_toupper(value);
  }

  const char* do_toupper(char* first, const char* last) const override {
    for (auto* current = first; current != last; ++current) {
      *current = do_toupper(*current);
    }
    return last;
  }
};

TEST(CTypeClassification, MasksAndScansDescribeCharactersWithoutParsingText) {
  const auto& facet =
      std::use_facet<std::ctype<char>>(std::locale::classic());
  const std::string text = "abc 42";
  std::array<std::ctype_base::mask, 6> masks{};

  EXPECT_TRUE(facet.is(std::ctype_base::alpha, 'A'));
  EXPECT_TRUE(facet.is(std::ctype_base::digit, '7'));
  EXPECT_TRUE(facet.is(std::ctype_base::space, '\n'));
  EXPECT_TRUE(facet.is(std::ctype_base::xdigit, 'f'));
  EXPECT_EQ(facet.scan_is(std::ctype_base::digit, text.data(), text.data() + text.size()),
            text.data() + 4);
  EXPECT_EQ(facet.scan_not(std::ctype_base::alpha, text.data(), text.data() + text.size()),
            text.data() + 3);
  EXPECT_EQ(facet.is(text.data(), text.data() + masks.size(), masks.data()),
            text.data() + masks.size());
  EXPECT_NE(masks[0] & std::ctype_base::alpha, 0);
  EXPECT_NE(masks[3] & std::ctype_base::space, 0);

  // mask 可组合，is(range) 一次写出每个字符的完整掩码；scan_is/scan_not 返回
  // 首个匹配位置或 last。它们按 locale 字符分类，不识别单词、数字或 Unicode 字素。
}

TEST(CTypeConversions, ScalarAndRangeOperationsShareTheFacetPolicy) {
  const auto& narrow =
      std::use_facet<std::ctype<char>>(std::locale::classic());
  const auto& wide =
      std::use_facet<std::ctype<wchar_t>>(std::locale::classic());
  std::array<char, 4> word{'A', 'b', 'C', '\0'};
  std::array<wchar_t, 3> widened{};
  std::array<char, 3> narrowed{};
  const std::array<char, 3> ascii{'A', 'z', '!'};

  EXPECT_EQ(narrow.tolower('Q'), 'q');
  EXPECT_EQ(narrow.tolower(word.data(), word.data() + 3), word.data() + 3);
  EXPECT_STREQ(word.data(), "abc");
  EXPECT_EQ(wide.widen(ascii.data(), ascii.data() + ascii.size(), widened.data()),
            ascii.data() + ascii.size());
  EXPECT_EQ(widened, (std::array<wchar_t, 3>{L'A', L'z', L'!'}));
  EXPECT_EQ(wide.narrow(widened.data(), widened.data() + widened.size(), '?', narrowed.data()),
            widened.data() + widened.size());
  EXPECT_EQ(narrowed, ascii);

  // widen/narrow 是 locale 的字符映射协议，不保证一般 Unicode 转码。narrow 对无法
  // 表示的字符写调用者给出的默认值；范围重载返回输入区间的末端而非输出长度。
}

TEST(CTypeCustomization, TableClassificationAndVirtualMappingsAreIndependent) {
  const std::locale teaching{std::locale::classic(), new TeachingCtype};
  const auto& facet = std::use_facet<std::ctype<char>>(teaching);
  std::array<char, 4> text{'a', 'b', '@', '\0'};

  EXPECT_TRUE(facet.is(std::ctype_base::alpha, '@'));
  EXPECT_EQ(facet.toupper('a'), '4');
  facet.toupper(text.data(), text.data() + 3);
  EXPECT_STREQ(text.data(), "4B@");
  EXPECT_TRUE(std::isalpha('@', teaching));
  EXPECT_EQ(std::toupper('a', teaching), '4');

  // ctype<char> 的分类可由 table 驱动，大小写映射则经虚函数分派；只修改 table
  // 不会自动定义新的大小写关系。locale 便利函数最终也查找对应 ctype<CharT>。
}

TEST(CTypeByName, NamedCFacetCanBeInstalledWithoutChangingGlobalClassification) {
  const std::locale named{
      std::locale::classic(),
      new std::ctype_byname<char>{"C"}};
  const auto& facet = std::use_facet<std::ctype<char>>(named);

  EXPECT_TRUE(facet.is(std::ctype_base::alpha, 'A'));
  EXPECT_EQ(facet.toupper('z'), 'Z');

  // ctype_byname 把分类和转换策略装进显式 locale，不修改进程 C locale。除 C 外的
  // 名称及其编码/字符表由系统提供，构造失败时抛 runtime_error。
}

TEST(CTypeConvenienceFunctions, UnsignedCharSelectsAMissingFacetInsteadOfPromoting) {
  const std::locale classic = std::locale::classic();
  const unsigned char byte = 'A';

  EXPECT_TRUE(std::isalpha('A', classic));
  EXPECT_THROW(static_cast<void>(std::isalpha(byte, classic)), std::bad_cast);

  // 带 locale 的 isalpha 是模板：unsigned char 会请求 ctype<unsigned char>，标准
  // locale 并不保证该 facet，于是抛 bad_cast。它不同于 <cctype> 要先转 unsigned char
  // 再以 int 调用的规则；这里通常应保留 char 类型或显式使用 ctype<char>。
}

TEST(CodecvtIdentity, CharSpecializationReportsThatNoConversionIsNecessary) {
  using Facet = std::codecvt<char, char, std::mbstate_t>;
  const auto& facet = std::use_facet<Facet>(std::locale::classic());
  std::mbstate_t state{};
  const std::string input = "plain bytes";
  const char* from_next = nullptr;
  std::array<char, 16> output{};
  char* to_next = nullptr;

  const auto result = facet.out(
      state,
      input.data(),
      input.data() + input.size(),
      from_next,
      output.data(),
      output.data() + output.size(),
      to_next);

  EXPECT_EQ(result, Facet::noconv);
  EXPECT_TRUE(facet.always_noconv());
  EXPECT_EQ(facet.encoding(), 1);
  EXPECT_EQ(facet.max_length(), 1);
  EXPECT_EQ(
      facet.length(
          state,
          input.data(),
          input.data() + input.size(),
          4),
      4);
  char* unshift_next = nullptr;
  EXPECT_EQ(
      facet.unshift(
          state,
          output.data(),
          output.data() + output.size(),
          unshift_next),
      Facet::noconv);

  // noconv 要求调用者直接使用原输入；length 返回最多产生 max 个内部字符可消费
  // 的外部长度，unshift 负责结束有状态编码。result 是协议状态，不是转换字符数。
}

TEST(CodecvtWideCharacters, StateAndNextPointersSupportIncrementalConversion) {
  using Facet = std::codecvt<wchar_t, char, std::mbstate_t>;
  const auto& facet = std::use_facet<Facet>(std::locale::classic());
  const std::wstring input = L"AZ";
  std::mbstate_t encode_state{};
  const wchar_t* wide_next = nullptr;
  std::array<char, 8> bytes{};
  char* byte_next = nullptr;

  EXPECT_EQ(
      facet.out(
          encode_state,
          input.data(),
          input.data() + input.size(),
          wide_next,
          bytes.data(),
          bytes.data() + bytes.size(),
          byte_next),
      Facet::ok);
  EXPECT_EQ(wide_next, input.data() + input.size());
  EXPECT_EQ(std::string(bytes.data(), byte_next), "AZ");

  std::mbstate_t decode_state{};
  const char* byte_read = nullptr;
  std::array<wchar_t, 4> decoded{};
  wchar_t* wide_written = nullptr;
  EXPECT_EQ(
      facet.in(
          decode_state,
          bytes.data(),
          byte_next,
          byte_read,
          decoded.data(),
          decoded.data() + decoded.size(),
          wide_written),
      Facet::ok);
  EXPECT_EQ(byte_read, byte_next);
  EXPECT_EQ(std::wstring(decoded.data(), wide_written), L"AZ");

  // mbstate_t、from_next 与 to_next 必须随分块调用一起保存；只看 result 会丢失
  // 已消费/已生成边界。classic C locale 的 ASCII 结果确定，但非 ASCII 依赖环境编码。
}

TEST(CodecvtByName, NamedCFacetCanBeInstalledWithoutChangingGlobalState) {
  using Facet = std::codecvt<wchar_t, char, std::mbstate_t>;
  const std::locale named{
      std::locale::classic(),
      new std::codecvt_byname<wchar_t, char, std::mbstate_t>{"C"}};
  const auto& facet = std::use_facet<Facet>(named);

  EXPECT_FALSE(facet.always_noconv());
  EXPECT_GE(facet.max_length(), 1);

  // *_byname 把操作系统 locale 名称封装进 facet，组合它不会调用 locale::global。
  // 除 "C" 外的名字是否安装属于部署能力，程序应在边界处捕获 runtime_error。
}

TEST(CodecvtUnicode, Utf8Utf16FacetDistinguishesOkPartialAndMalformedInput) {
  using Facet = std::codecvt_utf8_utf16<char16_t>;
  const Facet facet;
  const std::u16string input = u"A\u00e9\U0001f600";
  std::mbstate_t encode_state{};
  const char16_t* from_next = nullptr;
  std::array<char, 16> encoded{};
  char* to_next = nullptr;

  EXPECT_EQ(
      facet.out(
          encode_state,
          input.data(),
          input.data() + input.size(),
          from_next,
          encoded.data(),
          encoded.data() + encoded.size(),
          to_next),
      Facet::ok);
  EXPECT_EQ(from_next, input.data() + input.size());
  EXPECT_EQ(
      std::string(encoded.data(), to_next),
      std::string("A\xc3\xa9\xf0\x9f\x98\x80", 7));

  std::mbstate_t small_state{};
  const char16_t* small_next = nullptr;
  std::array<char, 2> small_output{};
  char* small_written = nullptr;
  EXPECT_EQ(
      facet.out(
          small_state,
          input.data() + 2,
          input.data() + input.size(),
          small_next,
          small_output.data(),
          small_output.data() + small_output.size(),
          small_written),
      Facet::partial);
  EXPECT_EQ(small_next, input.data() + 2);

  std::mbstate_t invalid_state{};
  const std::string invalid{"\xff", 1};
  const char* invalid_next = nullptr;
  std::array<char16_t, 2> decoded{};
  char16_t* decoded_next = nullptr;
  EXPECT_EQ(
      facet.in(
          invalid_state,
          invalid.data(),
          invalid.data() + invalid.size(),
          invalid_next,
          decoded.data(),
          decoded.data() + decoded.size(),
          decoded_next),
      Facet::error);

  // UTF facet 在 C++20 仍存在但自 C++17 已弃用；它按代码单元和缓冲边界工作，
  // partial 不等于非法输入。新代码宜选有明确错误策略且仍维护的 Unicode 库。
}

}  // namespace
