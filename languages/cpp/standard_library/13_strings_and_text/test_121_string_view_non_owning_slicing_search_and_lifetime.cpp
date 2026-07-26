// polyglot-covers:
// - cpp.stdlib.strings.string-view-construction-and-code-unit-range
// - cpp.stdlib.strings.string-view-contiguous-borrowed-range
// - cpp.stdlib.strings.string-view-non-owning-lifetime
// - cpp.stdlib.strings.string-view-data-and-null-termination-boundary
// - cpp.stdlib.strings.string-view-remove-prefix-suffix-and-substr
// - cpp.stdlib.strings.string-view-search-compare-prefix-and-suffix
// - cpp.stdlib.strings.string-view-literals-conversion-and-hashing
// - cpp.stdlib.strings.rvalue-owner-ranges-dangling-result

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <functional>
#include <ranges>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

std::string_view prefix_before(std::string_view text, char separator) {
  const auto position = text.find(separator);
  return text.substr(0, position);
}

TEST(StringViewConstruction, PointerAndCountCanDescribeDataWithoutATerminator) {
  const std::array<char, 4> bytes{'A', '\0', 'B', 'C'};
  const std::string_view counted{bytes.data(), bytes.size()};
  const std::string_view terminated{"A\0B"};

  EXPECT_EQ(counted.size(), 4U);
  EXPECT_EQ(counted[1], '\0');
  EXPECT_EQ(counted.back(), 'C');
  EXPECT_EQ(terminated.size(), 1U);

  // string_view 保存指针和长度，不要求尾部有零；单 C 字符串指针构造仍会调用
  // traits::length。对二进制或切片数据必须传入准确长度。
}

TEST(StringViewRanges, ItIsAReadOnlyContiguousViewAndABorrowedRange) {
  static_assert(std::ranges::view<std::string_view>);
  static_assert(std::ranges::borrowed_range<std::string_view>);
  static_assert(std::ranges::contiguous_range<std::string_view>);
  static_assert(std::ranges::sized_range<std::string_view>);
  static_assert(std::same_as<std::string_view::const_reference, const char&>);
  static_assert(std::same_as<std::ranges::range_reference_t<std::string_view>, const char&>);

  const std::string_view text{"abcd"};
  EXPECT_EQ(std::ranges::distance(text), 4);
  EXPECT_EQ(std::ranges::find(text, 'c'), text.begin() + 2);

  // view 的“只读”约束来自 const CharT 引用；底层对象可能由别处修改。
  // borrowed_range 表示销毁 string_view 包装对象不使迭代器失效，不代表字符存储永生。
}

TEST(StringViewLifetime, TheOwnerMustOutliveEveryViewAndIterator) {
  std::string owner{"alpha=42"};
  const std::string_view whole{owner};
  const auto key = prefix_before(whole, '=');

  EXPECT_EQ(key, "alpha");
  owner[0] = 'A';
  EXPECT_EQ(key, "Alpha");

  // view 不复制数据，所以能观察到等长原地修改。owner 销毁、重分配或被缩短到
  // 视图范围之外后，旧 view 会悬空；绝不能从局部 string 返回指向它的 view。
}

TEST(StringViewTermination, ASubviewEndIsUsuallyNotACStringBoundary) {
  const std::string owner{"key=value"};
  const std::string_view key{owner.data(), 3};

  EXPECT_EQ(key, "key");
  ASSERT_LT(key.size(), owner.size());
  EXPECT_EQ(key.data()[key.size()], '=');

  const std::string owned_copy{key};
  EXPECT_EQ(owned_copy.c_str()[owned_copy.size()], '\0');

  // string_view::data() 不承诺在 view 的 end 处终止。把子视图 data() 传给只接收
  // const char* 的 C API，会意外读取 '=value'；应传长度或先构造 owning string。
}

TEST(StringViewModifiers, RemovingEdgesChangesOnlyTheDescriptor) {
  const std::string owner{"[payload]"};
  std::string_view view{owner};

  view.remove_prefix(1);
  view.remove_suffix(1);

  EXPECT_EQ(view, "payload");
  EXPECT_EQ(owner, "[payload]");
  EXPECT_EQ(view.data(), owner.data() + 1);

  // remove_prefix/remove_suffix 是 O(1) 的指针和长度调整，不修改底层字符。
  // 参数大于 size 违反前置条件；处理不可信长度时要先夹取或检查。
}

TEST(StringViewSubstr, ItReturnsAnotherViewAndChecksOnlyTheStartingPosition) {
  const std::string owner{"abcdef"};
  const std::string_view whole{owner};
  const auto middle = whole.substr(2, 99);

  EXPECT_EQ(middle, "cdef");
  EXPECT_EQ(middle.data(), owner.data() + 2);
  EXPECT_TRUE(whole.substr(whole.size()).empty());
  EXPECT_THROW(whole.substr(whole.size() + 1), std::out_of_range);

  // count 会截到剩余长度，pos 大于 size 才抛异常。与 string::substr 不同，返回值
  // 仍引用原存储，不拥有字符，也不会自动补自己的终止符。
}

TEST(StringViewSearch, OperationsMirrorStringWithoutAllocating) {
  const std::string_view text{"abracadabra"};

  EXPECT_EQ(text.find("cad"), 4U);
  EXPECT_EQ(text.rfind("abra"), 7U);
  EXPECT_EQ(text.find_first_of("xyc"), 4U);
  EXPECT_EQ(text.find_first_not_of("abr"), 4U);
  EXPECT_TRUE(text.starts_with("abra"));
  EXPECT_TRUE(text.ends_with('a'));
  EXPECT_LT(text.compare("abracadabrz"), 0);

  // 查询语义与 basic_string 一致，也使用 traits；仍按代码单元而非 Unicode 字符。
  // C++20 有 starts_with/ends_with，但 contains 是 C++23 新增接口。
}

TEST(StringViewLiterals, SvSuffixPreservesLengthWithoutTakingOwnership) {
  using namespace std::string_view_literals;

  constexpr auto narrow = "A\0B"sv;
  constexpr auto utf8 = u8"猫"sv;

  static_assert(std::is_same_v<decltype(narrow), const std::string_view>);
  static_assert(std::is_same_v<decltype(utf8), const std::u8string_view>);
  static_assert(narrow.size() == 3);
  static_assert(utf8.size() == 3);

  EXPECT_EQ(narrow[1], '\0');

  // sv 指向静态存储期的字面量，所以该特例不会悬空；运行期缓冲区构造的 view
  // 没有同样寿命。后缀保留编译器已知长度，因而也保留内嵌零。
}

TEST(StringViewConversions, StringConvertsImplicitlyToViewButTheReverseOwnsAndIsExplicit) {
  static_assert(std::is_convertible_v<const std::string&, std::string_view>);
  static_assert(!std::is_convertible_v<std::string_view, std::string>);
  static_assert(std::is_constructible_v<std::string, std::string_view>);

  const std::string owner{"value"};
  const std::string_view view = owner;
  const std::string copy{view};

  EXPECT_EQ(copy, owner);
  EXPECT_EQ(std::hash<std::string_view>{}(view), std::hash<std::string_view>{}(copy));

  // 显式构造 string 提醒调用者发生分配与复制。相等 view 的 hash 必须相等，
  // 但散列数值同样不能持久化，也不能用“不同 hash”代替内容不相等判断。
}

TEST(StringViewDangling, AlgorithmsExposeTheDifferenceBetweenViewAndRvalueOwner) {
  using ViewResult = decltype(std::ranges::find(std::string_view{"abc"}, 'b'));
  using OwnerResult = decltype(std::ranges::find(std::string{"abc"}, 'b'));

  static_assert(std::same_as<ViewResult, std::string_view::iterator>);
  static_assert(std::same_as<OwnerResult, std::ranges::dangling>);

  // 临时 string 在算法返回时已销毁，因此 ranges 算法用 dangling 阻止取得迭代器；
  // 临时 string_view 只是描述符，返回迭代器仍指向其外部且在此例为静态存储的数据。
}

}  // namespace
