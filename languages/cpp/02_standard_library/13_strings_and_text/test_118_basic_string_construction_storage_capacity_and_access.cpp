// polyglot-covers:
// - cpp.stdlib.strings.basic-string-construction-and-embedded-null
// - cpp.stdlib.strings.basic-string-brace-versus-count-construction
// - cpp.stdlib.strings.basic-string-contiguous-storage-and-null-terminator
// - cpp.stdlib.strings.basic-string-iterator-and-range-properties
// - cpp.stdlib.strings.basic-string-size-capacity-reserve-and-resize
// - cpp.stdlib.strings.basic-string-element-access-contracts
// - cpp.stdlib.strings.basic-string-invalidation-and-sso-non-guarantees

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <iterator>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>

namespace {

TEST(BasicStringConstruction, PointerAndCountDecideWhetherEmbeddedNullIsData) {
  constexpr char raw[] = {'A', '\0', 'B', 'C', '\0'};
  const std::string null_terminated{raw};
  const std::string counted{raw, 4};
  const std::string from_range{std::begin(raw), std::begin(raw) + 4};

  EXPECT_EQ(null_terminated, "A");
  EXPECT_EQ(counted.size(), 4U);
  EXPECT_EQ(counted[1], '\0');
  EXPECT_EQ(counted, from_range);
  EXPECT_EQ(counted, std::string("A\0BC", 4));

  // 单指针构造把输入当 C 字符串，会在首个零字符停止；指针加长度与迭代器区间
  // 才能保存内嵌零。不要把来自外部缓冲区的“容量”误当成有效字符长度。
}

TEST(BasicStringConstruction, BracesCanSelectInitializerListInsteadOfCountAndValue) {
  const std::string repeated(5, 'x');
  const std::string two_code_units{5, 'x'};
  const std::string copied = repeated;
  std::string assigned;
  assigned = {'o', 'k'};

  EXPECT_EQ(repeated, "xxxxx");
  ASSERT_EQ(two_code_units.size(), 2U);
  EXPECT_EQ(two_code_units[0], static_cast<char>(5));
  EXPECT_EQ(two_code_units[1], 'x');
  EXPECT_EQ(copied, repeated);
  EXPECT_EQ(assigned, "ok");

  // (count, ch) 表示重复字符；{count, ch} 更优先匹配 initializer_list<char>，
  // 因而得到两个代码单元。这是把圆括号机械改成花括号时很隐蔽的语义变化。
}

TEST(BasicStringStorage, DataIsContiguousAndHasAReadableTrailingNull) {
  std::string text{"mutable"};

  static_assert(std::contiguous_iterator<std::string::iterator>);
  static_assert(std::ranges::contiguous_range<std::string>);
  static_assert(std::ranges::sized_range<std::string>);
  static_assert(std::is_same_v<decltype(std::as_const(text).data()), const char*>);
  static_assert(std::is_same_v<decltype(text.data()), char*>);

  EXPECT_EQ(text.data(), std::to_address(text.begin()));
  EXPECT_EQ(text.c_str(), text.data());
  EXPECT_EQ(text.data()[text.size()], '\0');

  text.data()[0] = 'M';
  EXPECT_EQ(text, "Mutable");

  // C++17 起非 const data() 可修改已有元素，适合与需要 char* 的受控 API 互操作。
  // 不能写越过 size，也不能把末尾哨兵改成非零；随后改变字符串还可能使旧指针失效。
}

TEST(BasicStringIteration, IteratorsVisitCodeUnitsAndReverseIteratorsInvertTraversal) {
  std::string text{"abcd"};
  std::array<char, 4> forward{};
  std::array<char, 4> reverse{};

  std::copy(text.begin(), text.end(), forward.begin());
  std::copy(text.rbegin(), text.rend(), reverse.begin());
  *text.begin() = 'A';

  EXPECT_EQ(forward, (std::array{'a', 'b', 'c', 'd'}));
  EXPECT_EQ(reverse, (std::array{'d', 'c', 'b', 'a'}));
  EXPECT_EQ(text, "Abcd");
  EXPECT_EQ(std::distance(text.begin(), text.end()), 4);

  // string 迭代器是随机访问且连续的，但单位仍是 CharT 代码单元；按迭代器前进
  // 不等于按 Unicode 码点或用户可见字符前进。
}

TEST(BasicStringCapacity, ReserveControlsMinimumCapacityButShrinkIsNonBinding) {
  std::string text{"abc"};
  const auto original_capacity = text.capacity();

  text.reserve(original_capacity + 40);
  const auto reserved_capacity = text.capacity();
  EXPECT_GE(reserved_capacity, original_capacity + 40);
  EXPECT_EQ(text, "abc");

  text.clear();
  EXPECT_TRUE(text.empty());
  EXPECT_GE(text.capacity(), reserved_capacity);

  text.shrink_to_fit();
  EXPECT_GE(text.capacity(), text.size());
  EXPECT_LE(text.capacity(), reserved_capacity);

  // capacity 至少为 size，但实现可以增长得更多；shrink_to_fit 也是非强制请求。
  // 小字符串优化、阈值以及 clear 后是否保留内存都不是可移植接口，不能写死地址。
}

TEST(BasicStringResize, GrowthValueInitializesNewCharactersAndShrinkRemovesTheSuffix) {
  std::string text{"ab"};

  text.resize(5);
  ASSERT_EQ(text.size(), 5U);
  EXPECT_EQ(text.substr(0, 2), "ab");
  EXPECT_EQ(text[2], '\0');
  EXPECT_EQ(text[4], '\0');

  text.resize(7, 'x');
  EXPECT_EQ(text.substr(5), "xx");
  text.resize(1);
  EXPECT_EQ(text, "a");

  // resize(n) 扩大时值初始化 char，因此新增的是字符串数据中的零字符，不只是
  // data()[size()] 的终止哨兵。需要可见填充值时使用 resize(n, ch)。
}

TEST(BasicStringAccess, CheckedAndUncheckedAccessHaveDifferentFailureContracts) {
  std::string text{"abc"};
  const auto& view = std::as_const(text);

  EXPECT_EQ(text.front(), 'a');
  EXPECT_EQ(text.back(), 'c');
  text.front() = 'A';
  text.back() = 'C';
  EXPECT_EQ(text, "AbC");
  EXPECT_EQ(view[view.size()], '\0');
  EXPECT_THROW(text.at(text.size()), std::out_of_range);

  // at 越界抛 out_of_range；operator[] 只对恰好 size 的 const 读取提供零哨兵。
  // 大于 size 的索引，以及对空字符串调用 front/back，均不能通过运行 UB 来演示。
}

TEST(BasicStringInvalidation, PositionsSurviveMutationMoreReliablyThanPointers) {
  std::string text{"key=value"};
  const auto separator = text.find('=');
  ASSERT_NE(separator, std::string::npos);

  const char* old_data = text.data();
  text.append(200, '!');

  EXPECT_EQ(text[separator], '=');
  EXPECT_EQ(text.substr(0, separator), "key");
  EXPECT_NE(text.data(), nullptr);
  (void)old_data;

  // 扩容型修改后不能解引用或比较旧指针、引用、迭代器所指内容；它们可能悬空。
  // 若业务锚点是逻辑位置，保存 size_type 索引并在修改后重新取得 data() 更稳妥。
}

}  // namespace
