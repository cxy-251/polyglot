// polyglot-covers:
// - cpp.stdlib.strings.cctype-classification-and-unsigned-char-domain
// - cpp.stdlib.strings.cctype-case-conversion-and-eof
// - cpp.stdlib.strings.cstring-length-and-lexicographical-comparison
// - cpp.stdlib.strings.cstring-character-substring-and-span-search
// - cpp.stdlib.strings.c-memory-copy-move-compare-search-and-fill
// - cpp.stdlib.strings.c-string-copy-concatenation-and-capacity-contract
// - cpp.stdlib.strings.strncpy-nontermination-trap
// - cpp.stdlib.strings.strtok-mutation-empty-field-and-hidden-state
// - cpp.stdlib.strings.strerror-static-message-contract

#include <gtest/gtest.h>

#include <array>
#include <cctype>
#include <cerrno>
#include <cstddef>
#include <cstring>
#include <string>
#include <string_view>

namespace {

std::string ascii_lowercase(std::string_view input) {
  std::string result;
  result.reserve(input.size());
  for (const char code_unit : input) {
    const auto safe = static_cast<unsigned char>(code_unit);
    result.push_back(static_cast<char>(std::tolower(safe)));
  }
  return result;
}

TEST(CCharacterClassification, PredicatesReturnNonzeroAndRequireARestrictedDomain) {
  EXPECT_NE(std::isalpha(static_cast<unsigned char>('A')), 0);
  EXPECT_NE(std::isdigit(static_cast<unsigned char>('7')), 0);
  EXPECT_NE(std::isxdigit(static_cast<unsigned char>('f')), 0);
  EXPECT_NE(std::isspace(static_cast<unsigned char>('\n')), 0);
  EXPECT_NE(std::isblank(static_cast<unsigned char>('\t')), 0);
  EXPECT_EQ(std::isdigit(static_cast<unsigned char>('x')), 0);

  const char possibly_negative = static_cast<char>(0xFF);
  EXPECT_EQ(ascii_lowercase(std::string_view{&possibly_negative, 1}).size(), 1U);

  // isalpha 等返回“零或非零”，不保证 true 恰好编码为 1。除 EOF 外，参数必须能
  // 表示为 unsigned char；直接传负的 signed char 是未定义行为，应先做无符号转换。
}

TEST(CCharacterConversion, CaseFunctionsReturnIntAndPreserveEof) {
  EXPECT_EQ(std::tolower(static_cast<unsigned char>('A')), 'a');
  EXPECT_EQ(std::toupper(static_cast<unsigned char>('z')), 'Z');
  EXPECT_EQ(std::tolower(EOF), EOF);
  EXPECT_EQ(ascii_lowercase("HeLLo"), "hello");

  // tolower/toupper 同样依赖当前 C locale，返回 int 以容纳 EOF。它们只转换一个
  // unsigned-char 值，不是 Unicode 大小写折叠，也不会处理多代码点映射。
}

TEST(CStringLength, NullTerminatedOperationsStopAtTheFirstZeroCodeUnit) {
  const char data[] = {'a', 'b', '\0', 'c', 'd', '\0'};

  EXPECT_EQ(std::strlen(data), 2U);
  EXPECT_LT(std::strcmp("abc", "abd"), 0);
  EXPECT_EQ(std::strncmp("abcX", "abcY", 3), 0);
  EXPECT_GT(std::strcmp("ab", "a"), 0);

  // strcmp 的结果只保证符号，不保证字符差值。所有 NTBS 函数都要求可达的终止零；
  // 对任意字节缓冲区调用 strlen/strcmp 会越界读取，应改用显式长度接口。
}

TEST(CStringSearch, CharacterSubstringAndSpanFunctionsAnswerDifferentQuestions) {
  const char text[] = "abracadabra";

  EXPECT_EQ(std::strchr(text, 'a'), text);
  EXPECT_EQ(std::strrchr(text, 'a'), text + 10);
  EXPECT_EQ(std::strchr(text, '\0'), text + std::strlen(text));
  EXPECT_EQ(std::strstr(text, "cada"), text + 4);
  EXPECT_EQ(std::strpbrk(text, "xyc"), text + 4);
  EXPECT_EQ(std::strspn("aaab42", "ab"), 4U);
  EXPECT_EQ(std::strcspn("key=value", "=:"), 3U);

  // strchr 可以查终止零；strpbrk 查集合中任一字符，strspn 查“全在集合内”的
  // 最长前缀，strcspn 则查“全不在集合内”的最长前缀。
}

TEST(CMemoryCopy, MemcpyCopiesDistinctRegionsAndMemmoveHandlesOverlap) {
  const std::array<unsigned char, 5> source{1, 2, 3, 4, 5};
  std::array<unsigned char, 5> copied{};

  EXPECT_EQ(std::memcpy(copied.data(), source.data(), source.size()), copied.data());
  EXPECT_EQ(copied, source);

  std::array<char, 6> overlapping{'a', 'b', 'c', 'd', 'e', '\0'};
  EXPECT_EQ(
      std::memmove(overlapping.data() + 1, overlapping.data(), 4),
      overlapping.data() + 1);
  EXPECT_STREQ(overlapping.data(), "aabcd");

  // memcpy 的区域重叠是未定义行为；memmove 按“仿佛先复制到临时数组”处理重叠。
  // 两者的 count 都按字节计算，不会调用对象的复制构造或赋值运算符。
}

TEST(CMemoryInspection, ComparisonUsesUnsignedBytesAndSearchReturnsAVoidPointer) {
  const std::array<unsigned char, 4> bytes{0x00, 0x7F, 0x80, 0xFF};
  const std::array<unsigned char, 4> same = bytes;
  const std::array<unsigned char, 4> lower{0x00, 0x7F, 0x7F, 0xFF};

  EXPECT_EQ(std::memcmp(bytes.data(), same.data(), bytes.size()), 0);
  EXPECT_GT(std::memcmp(bytes.data(), lower.data(), bytes.size()), 0);
  EXPECT_EQ(std::memchr(bytes.data(), 0x80, bytes.size()), bytes.data() + 2);
  EXPECT_EQ(std::memchr(bytes.data(), 0x42, bytes.size()), nullptr);

  // memcmp 按 unsigned char 逐字节比较，只能把零结果当“对象表示相同”。结构体
  // 可能含填充字节，浮点也可能有多种等价值表示，不能用 memcmp 代替值相等。
}

TEST(CMemoryFill, MemsetWritesARepeatedBytePatternRatherThanTypedValues) {
  std::array<unsigned char, 6> bytes{};

  EXPECT_EQ(std::memset(bytes.data(), 0xAB, bytes.size()), bytes.data());
  EXPECT_EQ(bytes, (std::array<unsigned char, 6>{0xAB, 0xAB, 0xAB, 0xAB, 0xAB, 0xAB}));

  // memset 的 int 值先转成 unsigned char，再重复写每个字节；把 int 数组填成 1
  // 不会得到整数 1。对非平凡对象写任意表示还可能破坏对象不变量。
}

TEST(CStringCopy, CallerMustProvideEnoughWritableStorageForCopyAndConcatenation) {
  std::array<char, 16> destination{};

  EXPECT_EQ(std::strcpy(destination.data(), "hello"), destination.data());
  EXPECT_EQ(std::strcat(destination.data(), " "), destination.data());
  EXPECT_EQ(std::strncat(destination.data(), "worldwide", 5), destination.data());
  EXPECT_STREQ(destination.data(), "hello world");

  // strcpy/strcat 不接收容量，目标太小会越界写；源和目标重叠也不允许。strncat 的
  // n 是最多追加的源字符数，函数仍会再写一个终止零，因此目标至少还需 n+1 空间。
}

TEST(CStringCopy, StrncpyCanFillTheBufferWithoutWritingATerminator) {
  std::array<char, 5> destination{'?', '?', '?', '?', '?'};

  EXPECT_EQ(std::strncpy(destination.data(), "hello", destination.size()), destination.data());
  EXPECT_EQ(destination, (std::array{'h', 'e', 'l', 'l', 'o'}));

  std::array<char, 6> padded{'?', '?', '?', '?', '?', '?'};
  std::strncpy(padded.data(), "hi", padded.size());
  EXPECT_EQ(padded, (std::array{'h', 'i', '\0', '\0', '\0', '\0'}));

  // strncpy 不是可靠的“带容量字符串复制”：源长度达到 n 时不写终止零；较短时
  // 又用零填满余下空间。若要截断 NTBS，必须显式保证最后一字节为零。
}

TEST(CStringTokenization, StrtokMutatesInputCollapsesDelimitersAndKeepsHiddenState) {
  char text[] = "alpha,,beta;gamma";

  const char* first = std::strtok(text, ",;");
  const char* second = std::strtok(nullptr, ",;");
  const char* third = std::strtok(nullptr, ",;");
  const char* end = std::strtok(nullptr, ",;");

  ASSERT_NE(first, nullptr);
  ASSERT_NE(second, nullptr);
  ASSERT_NE(third, nullptr);
  EXPECT_STREQ(first, "alpha");
  EXPECT_STREQ(second, "beta");
  EXPECT_STREQ(third, "gamma");
  EXPECT_EQ(end, nullptr);
  EXPECT_EQ(text[5], '\0');

  // strtok 把分隔符改成零并用隐藏状态继续扫描；相邻分隔符不会产生空字段。
  // 嵌套解析、只读字面量和需要保留原文的代码应使用显式索引或 string_view 切片。
}

TEST(CStringErrors, StrerrorReturnsImplementationTextWithSharedStorageSemantics) {
  const char* message = std::strerror(EDOM);

  ASSERT_NE(message, nullptr);
  EXPECT_GT(std::strlen(message), 0U);

  // 错误文字由实现和 locale 决定，且后续 strerror 调用可能覆盖同一内部缓冲区。
  // 测试应判断错误码，日志若需长期保存则立即复制字符串，不应断言完整英文措辞。
}

}  // namespace
