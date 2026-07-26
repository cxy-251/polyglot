// polyglot-covers:
// - cpp.stdlib.strings.char-traits-required-types-and-operations
// - cpp.stdlib.strings.char-traits-sequence-copy-move-assign
// - cpp.stdlib.strings.char-traits-eof-and-int-type-domain
// - cpp.stdlib.strings.char-traits-standard-code-unit-specializations
// - cpp.stdlib.strings.code-units-versus-unicode-code-points
// - cpp.stdlib.strings.custom-character-traits-protocol-dispatch

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

constexpr char ascii_lower(char value) {
  if (value >= 'A' && value <= 'Z') {
    return static_cast<char>(value - 'A' + 'a');
  }
  return value;
}

struct AsciiCaseInsensitiveTraits : std::char_traits<char> {
  static constexpr bool eq(char left, char right) {
    return ascii_lower(left) == ascii_lower(right);
  }

  static constexpr bool lt(char left, char right) {
    return ascii_lower(left) < ascii_lower(right);
  }

  static constexpr int compare(const char* left, const char* right, std::size_t count) {
    for (std::size_t index = 0; index < count; ++index) {
      if (lt(left[index], right[index])) {
        return -1;
      }
      if (lt(right[index], left[index])) {
        return 1;
      }
    }
    return 0;
  }

  static constexpr const char* find(const char* text, std::size_t count, char target) {
    for (std::size_t index = 0; index < count; ++index) {
      if (eq(text[index], target)) {
        return text + index;
      }
    }
    return nullptr;
  }
};

using CaseInsensitiveString = std::basic_string<char, AsciiCaseInsensitiveTraits>;

TEST(CharacterTraitsTypes, StandardSpecializationExposesTheSequenceProtocolTypes) {
  using Traits = std::char_traits<char>;

  static_assert(std::is_same_v<Traits::char_type, char>);
  static_assert(std::is_integral_v<Traits::int_type>);
  static_assert(std::is_integral_v<Traits::off_type>);
  static_assert(std::is_same_v<Traits::pos_type, std::streampos>);
  static_assert(std::is_same_v<Traits::state_type, std::mbstate_t>);

  EXPECT_TRUE(Traits::eq('x', 'x'));
  EXPECT_TRUE(Traits::lt('a', 'b'));
  EXPECT_LT(Traits::compare("abc", "abd", 3), 0);
  EXPECT_EQ(Traits::length("a\0hidden"), 1U);
  EXPECT_EQ(Traits::find("paper", 5, 'p'), std::string_view{"paper"}.data());

  // char_traits 是 basic_string、basic_string_view 与流共享的字符序列协议。
  // compare 的负、零、正才有语义，具体负值不要求恰好等于 -1。
}

TEST(CharacterTraitsSequences, CopyMoveAndAssignHaveDifferentOverlapContracts) {
  using Traits = std::char_traits<char>;
  char copied[6]{};
  const char source[] = "abcde";

  EXPECT_EQ(Traits::copy(copied, source, 5), copied);
  EXPECT_STREQ(copied, "abcde");

  char overlapping[] = "abcde";
  EXPECT_EQ(Traits::move(overlapping + 1, overlapping, 4), overlapping + 1);
  EXPECT_STREQ(overlapping, "aabcd");

  Traits::assign(overlapping[0], 'z');
  Traits::assign(overlapping + 1, 3, 'x');
  EXPECT_STREQ(overlapping, "zxxxd");

  // copy 与 memcpy 一样要求源、目标不重叠；重叠搬移必须用 move。
  // count 为零时允许不解引用指针，但实际代码仍应避免制造无效指针值。
}

TEST(CharacterTraitsEof, IntTypeCanRepresentEveryCodeUnitAndASeparateEndMarker) {
  using Traits = std::char_traits<char>;
  const auto letter = Traits::to_int_type('A');
  const auto eof = Traits::eof();

  EXPECT_TRUE(Traits::eq_int_type(letter, Traits::to_int_type('A')));
  EXPECT_FALSE(Traits::eq_int_type(letter, eof));
  EXPECT_EQ(Traits::to_char_type(letter), 'A');
  EXPECT_FALSE(Traits::eq_int_type(Traits::not_eof(eof), eof));
  EXPECT_TRUE(Traits::eq_int_type(Traits::not_eof(letter), letter));

  // 流不能用 char 本身同时表示所有字符和 EOF，因此先提升到 int_type。
  // 不要把 eof 强制转回 char 后比较：该结果不能再可靠地区分真实代码单元。
}

TEST(CharacterTraitsEncodings, SpecializationsCountCodeUnitsRatherThanDisplayedCharacters) {
  static_assert(std::is_same_v<std::char_traits<char8_t>::char_type, char8_t>);
  static_assert(std::is_same_v<std::char_traits<char16_t>::char_type, char16_t>);
  static_assert(std::is_same_v<std::char_traits<char32_t>::char_type, char32_t>);
  static_assert(!std::is_same_v<char8_t, char>);

  EXPECT_EQ(std::char_traits<char8_t>::length(u8"猫"), 3U);
  EXPECT_EQ(std::char_traits<char16_t>::length(u"😀"), 2U);
  EXPECT_EQ(std::char_traits<char32_t>::length(U"😀"), 1U);

  // UTF-8 的一个码点可占多个 char8_t，UTF-16 的补充平面码点是代理项对。
  // length 只寻找零代码单元；它不会验证编码，也不会统计用户看到的字素簇。
}

TEST(CustomCharacterTraits, BasicStringDelegatesComparisonAndSearchingToItsTraits) {
  const CaseInsensitiveString first{"Alpha"};
  const CaseInsensitiveString same_letters{"aLPHA"};
  const CaseInsensitiveString later{"beta"};

  EXPECT_EQ(first, same_letters);
  EXPECT_LT(first, later);
  EXPECT_EQ(first.find('P'), 2U);
  EXPECT_EQ(first.find("HA"), 3U);

  const std::string ordinary_first{first.data(), first.size()};
  const std::string ordinary_second{same_letters.data(), same_letters.size()};
  EXPECT_NE(ordinary_first, ordinary_second);

  // traits 是 basic_string 类型的一部分；不同 traits 的字符串不是可随意混用的同一类型。
  // 这里只改变 ASCII 比较协议，不声称能完成 Unicode 大小写折叠或语言相关排序。
}

}  // namespace
