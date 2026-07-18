// polyglot-covers:
// - cpp.stdlib.strings.basic-string-append-insert-and-self-reference
// - cpp.stdlib.strings.basic-string-erase-replace-and-copy
// - cpp.stdlib.strings.basic-string-push-pop-and-swap
// - cpp.stdlib.strings.basic-string-find-family-and-empty-pattern
// - cpp.stdlib.strings.basic-string-npos-sentinel
// - cpp.stdlib.strings.basic-string-substr-and-bounds
// - cpp.stdlib.strings.basic-string-compare-and-cpp20-prefix-suffix
// - cpp.stdlib.strings.basic-string-nonmember-concatenation-and-comparison
// - cpp.stdlib.strings.erase-and-erase-if

#include <gtest/gtest.h>

#include <array>
#include <compare>
#include <limits>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

template <class Left, class Right>
concept Addable = requires(Left left, Right right) { left + right; };

TEST(BasicStringAppend, OverloadsDistinguishWholeStringsSubrangesAndRepeatedCharacters) {
  std::string text{"root"};
  const std::string source{"/alpha/beta"};

  text += ':';
  text.append(source, 0, 6);
  text.append(2, '!');
  text.append({'?', '?'});

  EXPECT_EQ(text, "root:/alpha!!??");

  std::string self{"abc"};
  self.append(self, 0, 2);
  EXPECT_EQ(self, "abcab");

  // append(str, pos, count) 的 pos 属于源字符串，而 append(count, ch) 表示重复。
  // 标准成员函数处理来自自身的子范围；直接用失效的 data 指针拼接则没有这种保障。
}

TEST(BasicStringInsert, PositionAndIteratorOverloadsReturnDifferentKindsOfResult) {
  std::string text{"ace"};

  auto& same = text.insert(1, "BCD", 2);
  EXPECT_EQ(&same, &text);
  EXPECT_EQ(text, "aBCce");

  const auto inserted = text.insert(text.begin() + 1, '-');
  EXPECT_EQ(*inserted, '-');
  text.insert(text.end(), 2, '!');
  EXPECT_EQ(text, "a-BCce!!");

  // 按索引的重载返回 *this；按迭代器插入一个字符则返回新字符位置。
  // 插入可能重分配，调用前取得的迭代器不能在调用后继续参与位置计算。
}

TEST(BasicStringErase, IndexAndIteratorFormsExposeDifferentContinuationPatterns) {
  std::string text{"0123456789"};

  auto& same = text.erase(2, 3);
  EXPECT_EQ(&same, &text);
  EXPECT_EQ(text, "0156789");

  auto next = text.erase(text.begin() + 2);
  EXPECT_EQ(*next, '6');
  next = text.erase(next, next + 2);
  EXPECT_EQ(*next, '8');
  EXPECT_EQ(text, "0189");

  text.erase(2);
  EXPECT_EQ(text, "01");

  // erase(pos) 的 count 默认到结尾；区间重载返回被删区间之后的新位置，便于循环删除。
  // pos 大于 size 会抛异常，而迭代器不属于当前字符串属于前置条件违例。
}

TEST(BasicStringReplace, ReplacementLengthNeedNotMatchTheRemovedLength) {
  std::string text{"name=old;"};
  const std::string replacement{"new-value"};

  text.replace(5, 3, replacement);
  EXPECT_EQ(text, "name=new-value;");

  text.replace(text.begin(), text.begin() + 4, 2, 'x');
  EXPECT_EQ(text, "xx=new-value;");

  text.replace(3, 9, "fresh-data", 5);
  EXPECT_EQ(text, "xx=fresh;");

  // replace 同时完成删除和插入，不要求长度相等。指针加 count 重载只取源缓冲区
  // 的前 count 个字符；不要误把它当成目标字符串的删除数量。
}

TEST(BasicStringCopy, ItCopiesRawCharactersWithoutAppendingANullTerminator) {
  const std::string text{"sample"};
  std::array<char, 5> destination{'?', '?', '?', '?', '?'};

  const auto copied = text.copy(destination.data(), 3, 1);

  EXPECT_EQ(copied, 3U);
  EXPECT_EQ(destination, (std::array{'a', 'm', 'p', '?', '?'}));
  EXPECT_THROW(text.copy(destination.data(), 1, text.size() + 1), std::out_of_range);

  // copy 的目标是裸缓冲区，只复制字符并返回数量；调用者必须自己留空间和写终止符。
  // count 超过剩余内容时会截断，但 pos 超过 size 时仍抛 out_of_range。
}

TEST(BasicStringEnds, PushBackAndPopBackOperateOnExactlyOneCodeUnit) {
  std::string text{"ab"};

  text.push_back('c');
  EXPECT_EQ(text, "abc");
  text.pop_back();
  EXPECT_EQ(text, "ab");

  std::string other{"right"};
  text.swap(other);
  EXPECT_EQ(text, "right");
  EXPECT_EQ(other, "ab");

  // pop_back 对空字符串没有可检查的失败返回，调用前必须保证非空。
  // swap 交换完整值；自定义 allocator 时还要考虑其传播规则，不能假定逐字符复制。
}

TEST(BasicStringFind, SearchFamilyExpressesDirectionAndCharacterSetQueries) {
  const std::string text{"abracadabra"};

  EXPECT_EQ(text.find("abra"), 0U);
  EXPECT_EQ(text.find("abra", 1), 7U);
  EXPECT_EQ(text.rfind("abra"), 7U);
  EXPECT_EQ(text.find_first_of("cd"), 4U);
  EXPECT_EQ(text.find_last_of("bc"), 8U);
  EXPECT_EQ(text.find_first_not_of("abr"), 4U);
  EXPECT_EQ(text.find_last_not_of("abr"), 6U);
  EXPECT_EQ(text.find('z'), std::string::npos);

  // find_first_of 查“集合中的任意字符”，不是查整个子串；查子串使用 find。
  // 所有位置都是代码单元索引，UTF-8 文本中不能直接当作字符序号。
}

TEST(BasicStringFind, EmptyPatternAndStartingPositionHaveDefinedBoundaryRules) {
  const std::string text{"abc"};

  EXPECT_EQ(text.find("", 0), 0U);
  EXPECT_EQ(text.find("", text.size()), text.size());
  EXPECT_EQ(text.find("", text.size() + 1), std::string::npos);
  EXPECT_EQ(text.rfind(""), text.size());
  EXPECT_EQ(text.rfind("", 1), 1U);

  // 空模式可在字符之间匹配，包括尾后位置；但正向搜索的起点不能超过 size。
  // rfind 的 pos 表示候选起点上限，不是从左边跳过的字符数量。
}

TEST(BasicStringNpos, SentinelIsTheMaximumSizeTypeAndMustNotBeUsedAsAnIndex) {
  static_assert(std::string::npos == std::numeric_limits<std::string::size_type>::max());

  const std::string text{"key=value"};
  const auto missing = text.find(':');
  EXPECT_EQ(missing, std::string::npos);

  std::string suffix = "unchanged";
  if (missing != std::string::npos) {
    suffix = text.substr(missing + 1);
  }
  EXPECT_EQ(suffix, "unchanged");

  // npos + 1 会按无符号算术回绕成 0；先加一再判断会把“未找到”伪装成开头。
}

TEST(BasicStringSubstr, CountIsClampedButStartingPositionIsChecked) {
  const std::string text{"abcdef"};

  EXPECT_EQ(text.substr(2, 99), "cdef");
  EXPECT_EQ(text.substr(text.size()), "");
  EXPECT_THROW(text.substr(text.size() + 1), std::out_of_range);

  auto copy = text.substr(1, 3);
  copy[0] = 'X';
  EXPECT_EQ(copy, "Xcd");
  EXPECT_EQ(text, "abcdef");

  // substr 返回拥有自己存储的新 string，而不是视图；只想无分配切片时用 string_view。
}

TEST(BasicStringComparison, LexicographicalOrderingIncludesEmbeddedNulls) {
  const std::string short_value{"ab"};
  const std::string longer{"abc"};
  const std::string with_null{"ab\0z", 4};
  const std::string other_null{"ab\0y", 4};

  EXPECT_LT(short_value.compare(longer), 0);
  EXPECT_GT(with_null.compare(other_null), 0);
  EXPECT_TRUE(longer.starts_with("ab"));
  EXPECT_TRUE(longer.ends_with('c'));
  EXPECT_FALSE(longer.ends_with("bcx"));
  EXPECT_EQ(short_value <=> longer, std::strong_ordering::less);

  // string 比较使用长度与 traits，不会在内嵌零处停止。starts_with/ends_with 是
  // C++20 接口；contains 到 C++23 才加入，锁定版本不应假装已有。
}

TEST(BasicStringNonMembers, ConcatenationRequiresAnOwningStringOperandInCxx20) {
  using namespace std::string_literals;

  const auto first = "path/"s + "file";
  const auto second = '<' + first + '>';

  EXPECT_EQ(first, "path/file");
  EXPECT_EQ(second, "<path/file>");
  static_assert(Addable<std::string, const char*>);
  static_assert(!Addable<std::string, std::string_view>);

  // C++20 没有 string + string_view 重载；可显式构造 string，或 append(view.data(),
  // view.size())。至少一个拥有型 string 操作数也避免退化成两个裸指针相加。
}

TEST(BasicStringErasure, Cxx20FreeFunctionsReturnTheNumberOfRemovedCharacters) {
  std::string text{"banana"};

  const auto removed_a = std::erase(text, 'a');
  const auto removed_n = std::erase_if(text, [](char value) { return value == 'n'; });

  EXPECT_EQ(removed_a, 3U);
  EXPECT_EQ(removed_n, 2U);
  EXPECT_EQ(text, "b");

  // std::erase/erase_if 封装 erase-remove 惯用法并返回删除数量，不要再对结果调用
  // 成员 erase；谓词仍应无副作用且不能依赖元素被访问的精确次数。
}

}  // namespace
