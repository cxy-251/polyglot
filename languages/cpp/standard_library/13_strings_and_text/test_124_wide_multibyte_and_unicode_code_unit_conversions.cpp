// polyglot-covers:
// - cpp.stdlib.strings.wide-character-classification-and-case
// - cpp.stdlib.strings.wide-string-and-wide-memory-operations
// - cpp.stdlib.strings.wide-numeric-conversion-and-end-pointer
// - cpp.stdlib.strings.mbrtowc-wcrtomb-state-and-return-codes
// - cpp.stdlib.strings.mbsrtowcs-wcsrtombs-source-pointer-protocol
// - cpp.stdlib.strings.btowc-wctob-single-byte-boundary
// - cpp.stdlib.strings.mbrtoc16-c16rtomb-code-unit-conversion
// - cpp.stdlib.strings.mbrtoc32-c32rtomb-code-unit-conversion
// - cpp.stdlib.strings.c-multibyte-global-locale-trap

#include <gtest/gtest.h>

#include <array>
#include <cerrno>
#include <climits>
#include <clocale>
#include <cstddef>
#include <cstdlib>
#include <cuchar>
#include <cwchar>
#include <cwctype>
#include <limits>
#include <string_view>

#if defined(__APPLE__)
#define POLYGLOT_HAS_CUCHAR_CONVERSIONS 0
#else
#define POLYGLOT_HAS_CUCHAR_CONVERSIONS 1
#endif

namespace {

void select_classic_c_locale() {
  ASSERT_NE(std::setlocale(LC_ALL, "C"), nullptr);
}

TEST(WideCharacterClassification, PredicatesAndCaseConversionRemainLocaleDependent) {
  select_classic_c_locale();

  EXPECT_NE(std::iswalpha(L'A'), 0);
  EXPECT_NE(std::iswdigit(L'7'), 0);
  EXPECT_NE(std::iswspace(L'\n'), 0);
  EXPECT_EQ(std::towlower(L'A'), L'a');
  EXPECT_EQ(std::towupper(L'z'), L'Z');
  EXPECT_EQ(std::towlower(WEOF), WEOF);

  // isw*/tow* 的域是 wint_t 或 WEOF，行为仍取决于全局 C locale；wchar_t 宽
  // 并不意味着函数自动实现完整 Unicode 属性或多字符大小写映射。
}

TEST(WideStrings, NullTerminatedSearchAndComparisonMirrorNarrowCStringOperations) {
  const wchar_t text[] = L"abracadabra";

  EXPECT_EQ(std::wcslen(text), 11U);
  EXPECT_LT(std::wcscmp(L"abc", L"abd"), 0);
  EXPECT_EQ(std::wcsncmp(L"abcX", L"abcY", 3), 0);
  EXPECT_EQ(std::wcschr(text, L'c'), text + 4);
  EXPECT_EQ(std::wcsrchr(text, L'a'), text + 10);
  EXPECT_EQ(std::wcsstr(text, L"cada"), text + 4);
  EXPECT_EQ(std::wcsspn(L"aaab42", L"ab"), 4U);
  EXPECT_EQ(std::wcscspn(L"key=value", L"=:"), 3U);

  // 这些函数的边界仍是首个 L'\0'，结果比较也只保证符号；它们按 wchar_t
  // 代码单元工作，不负责规范化或字素簇比较。
}

TEST(WideMemory, WmemmoveHandlesOverlapAndCountsWideElementsRatherThanBytes) {
  std::array<wchar_t, 6> text{L'a', L'b', L'c', L'd', L'e', L'\0'};
  std::array<wchar_t, 6> copy{};

  EXPECT_EQ(std::wmemcpy(copy.data(), text.data(), text.size()), copy.data());
  EXPECT_EQ(copy, text);
  EXPECT_EQ(std::wmemmove(text.data() + 1, text.data(), 4), text.data() + 1);
  EXPECT_STREQ(text.data(), L"aabcd");
  EXPECT_EQ(std::wmemchr(text.data(), L'c', text.size()), text.data() + 3);
  EXPECT_GT(std::wmemcmp(L"abd", L"abc", 3), 0);
  std::wmemset(copy.data(), L'x', 3);
  EXPECT_EQ(copy[0], L'x');
  EXPECT_EQ(copy[2], L'x');

  // wmem* 的 count 以 wchar_t 元素计，不是字节数；wmemcpy 的重叠限制与 memcpy
  // 相同，重叠时使用 wmemmove。
}

TEST(WideNumericConversions, EndPointerDistinguishesPrefixSuccessFromWholeFieldSuccess) {
  wchar_t* integer_end = nullptr;
  const long integer = std::wcstol(L"  -0x2a rest", &integer_end, 0);

  EXPECT_EQ(integer, -42L);
  ASSERT_NE(integer_end, nullptr);
  EXPECT_EQ(std::wstring_view(integer_end), L" rest");

  wchar_t* floating_end = nullptr;
  const double floating = std::wcstod(L"1.25e2ms", &floating_end);
  EXPECT_DOUBLE_EQ(floating, 125.0);
  EXPECT_EQ(std::wstring_view(floating_end), L"ms");

  // wcsto* 对宽字符串提供与 strto* 相同的 locale 相关前缀解析。调用前清 errno，
  // 并同时检查 end 与 ERANGE，才能区分零值、无转换、尾缀和范围错误。
}

TEST(MultibyteSingleCharacter, StateAndReturnCodesDescribeProgressNotJustSuccess) {
  select_classic_c_locale();
  std::mbstate_t state{};
  wchar_t wide = L'?';

  EXPECT_EQ(std::mbrtowc(&wide, "A", 1, &state), 1U);
  EXPECT_EQ(wide, L'A');
  EXPECT_EQ(std::mbsinit(&state), 1);

  const auto incomplete = std::mbrtowc(&wide, "B", 0, &state);
  EXPECT_EQ(incomplete, std::numeric_limits<std::size_t>::max() - 1);

  const char invalid[] = {static_cast<char>(0xFF), '\0'};
  const auto invalid_result = std::mbrtowc(&wide, invalid, 1, &state);
  EXPECT_EQ(invalid_result, std::numeric_limits<std::size_t>::max());

  // size_t(-2) 表示输入不完整，size_t(-1) 表示非法序列；返回类型无符号，不能拿
  // 结果简单判断 >0。转换错误后的 mbstate_t 状态未指定，继续前应重新零初始化。
}

TEST(MultibyteOutput, WcrtombWritesOneLocaleEncodedCharacterAndCanResetState) {
  select_classic_c_locale();
  std::mbstate_t state{};
  std::array<char, MB_LEN_MAX> buffer{};

  const auto count = std::wcrtomb(buffer.data(), L'Z', &state);
  ASSERT_EQ(count, 1U);
  EXPECT_EQ(buffer[0], 'Z');
  EXPECT_EQ(std::mbsinit(&state), 1);
  EXPECT_EQ(std::wcrtomb(nullptr, L'\0', &state), 1U);

  // 输出缓冲区至少要有 MB_CUR_MAX 字节；C locale 中 ASCII 是一字节，但其他
  // locale 可使用状态编码。传空目标请求写入恢复初始移位状态所需的序列。
}

TEST(MultibyteSequences, SourcePointerBecomesNullOnlyAfterTheTerminatorIsConverted) {
  select_classic_c_locale();
  std::mbstate_t to_wide_state{};
  const char* narrow_source = "alpha";
  std::array<wchar_t, 8> wide{};

  const auto wide_count =
      std::mbsrtowcs(wide.data(), &narrow_source, wide.size(), &to_wide_state);
  EXPECT_EQ(wide_count, 5U);
  EXPECT_EQ(narrow_source, nullptr);
  EXPECT_STREQ(wide.data(), L"alpha");

  std::mbstate_t to_narrow_state{};
  const wchar_t* wide_source = wide.data();
  std::array<char, 8> narrow{};
  const auto narrow_count =
      std::wcsrtombs(narrow.data(), &wide_source, narrow.size(), &to_narrow_state);
  EXPECT_EQ(narrow_count, 5U);
  EXPECT_EQ(wide_source, nullptr);
  EXPECT_STREQ(narrow.data(), "alpha");

  // 成功转换终止零后，函数把 *src 设为空；若目标空间先耗尽，*src 指向尚未转换
  // 的位置，调用者可保留同一 state 分块续传。返回数量不包含写入的终止零。
}

TEST(SingleByteWideBoundary, BtowcAndWctobOnlyRepresentSingleByteCharacters) {
  select_classic_c_locale();

  EXPECT_EQ(std::btowc('A'), L'A');
  EXPECT_EQ(std::wctob(L'A'), 'A');
  EXPECT_EQ(std::btowc(EOF), WEOF);
  EXPECT_EQ(std::wctob(WEOF), EOF);

  // btowc/wctob 只处理初始移位状态下恰好一个字节可表示的字符，不是通用 UTF
  // 转码器；多字节文本必须使用带 mbstate_t 的 mbr*/c*rtomb 系列。
}

TEST(Utf16CodeUnitConversion, CucharFunctionsUseTheActiveCEncodingAndExplicitState) {
#if POLYGLOT_HAS_CUCHAR_CONVERSIONS
  select_classic_c_locale();
  std::mbstate_t decode_state{};
  char16_t code_unit = u'?';

  EXPECT_EQ(std::mbrtoc16(&code_unit, "A", 1, &decode_state), 1U);
  EXPECT_EQ(code_unit, u'A');

  std::mbstate_t encode_state{};
  std::array<char, MB_LEN_MAX> output{};
  EXPECT_EQ(std::c16rtomb(output.data(), u'A', &encode_state), 1U);
  EXPECT_EQ(output[0], 'A');

  // mbrtoc16 面对需要代理项对的字符时可能先返回首个 char16_t，再以 size_t(-3)
  // 交付内部状态中的下一代码单元；不能假设一次调用总对应一个 Unicode 码点。
#else
  GTEST_SKIP() << "The host Apple SDK used only by clangd omits the C11 uchar conversions";
#endif
}

TEST(Utf32CodeUnitConversion, OneChar32ValueStillDependsOnTheActiveMultibyteEncoding) {
#if POLYGLOT_HAS_CUCHAR_CONVERSIONS
  select_classic_c_locale();
  std::mbstate_t decode_state{};
  char32_t code_unit = U'?';

  EXPECT_EQ(std::mbrtoc32(&code_unit, "Z", 1, &decode_state), 1U);
  EXPECT_EQ(code_unit, U'Z');

  std::mbstate_t encode_state{};
  std::array<char, MB_LEN_MAX> output{};
  EXPECT_EQ(std::c32rtomb(output.data(), U'Z', &encode_state), 1U);
  EXPECT_EQ(output[0], 'Z');

  // char32_t 能容纳 Unicode 标量值不等于当前 C locale 能编码它。这里用 C locale
  // 的 ASCII 保持确定性；真实 UTF-8 工作流必须显式选择并验证可用 locale。
#else
  GTEST_SKIP() << "The host Apple SDK used only by clangd omits the C11 uchar conversions";
#endif
}

TEST(CLocaleState, SetlocaleIsProcessGlobalAndQueriesReturnBorrowedStorage) {
  select_classic_c_locale();
  const char* current = std::setlocale(LC_CTYPE, nullptr);

  ASSERT_NE(current, nullptr);
  EXPECT_EQ(std::string_view(current), "C");
  EXPECT_GE(MB_CUR_MAX, 1);

  // setlocale 修改进程级状态，返回指针也可能被下一次调用覆盖；并发库代码不应在
  // 热路径切换它。C++ locale 对象和 facet 能把许多本地化操作变成显式依赖。
}

}  // namespace
