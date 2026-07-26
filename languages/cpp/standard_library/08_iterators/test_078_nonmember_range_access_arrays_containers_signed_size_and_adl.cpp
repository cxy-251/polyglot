// polyglot-covers:
// - cpp.stdlib.iterators.std-begin-end-container-and-array-overloads
// - cpp.stdlib.iterators.std-cbegin-cend-const-access
// - cpp.stdlib.iterators.std-rbegin-rend-and-reverse-array-access
// - cpp.stdlib.iterators.std-size-and-ssize-signed-difference
// - cpp.stdlib.iterators.std-empty-container-array-and-initializer-list
// - cpp.stdlib.iterators.std-data-container-array-and-initializer-list
// - cpp.stdlib.iterators.range-access-adl-using-std-pattern
// - cpp.stdlib.iterators.initializer-list-range-access-lifetime

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <initializer_list>
#include <iterator>
#include <numeric>
#include <type_traits>
#include <utility>
#include <vector>

namespace adl_buffer {

struct Buffer {
  int values[3];
};

int* begin(Buffer& buffer) noexcept {
  return buffer.values;
}

int* end(Buffer& buffer) noexcept {
  return buffer.values + 3;
}

const int* begin(const Buffer& buffer) noexcept {
  return buffer.values;
}

const int* end(const Buffer& buffer) noexcept {
  return buffer.values + 3;
}

}  // namespace adl_buffer

namespace {

template <class Range>
int SumWithAdl(Range& range) {
  using std::begin;
  using std::end;
  return std::accumulate(begin(range), end(range), 0);
}

TEST(RangeAccess, BeginAndEndHandleBothContainersAndBuiltInArrays) {
  std::vector<int> container{1, 2, 3};
  int array[] = {4, 5, 6};

  EXPECT_EQ(std::begin(container), container.begin());
  EXPECT_EQ(std::end(container), container.end());
  EXPECT_EQ(std::begin(array), array);
  EXPECT_EQ(std::end(array), array + 3);

  *std::begin(container) = 10;
  *std::begin(array) = 40;
  EXPECT_EQ(container.front(), 10);
  EXPECT_EQ(array[0], 40);

  // std::begin/end 对容器调用成员，对内建 T[N] 返回指针边界，使泛型代码不必把数组
  // 先退化成会丢失长度的 T*。数组必须以引用传入，退化后的裸指针没有可推导的 end。
}

TEST(RangeAccess, CbeginAndCendForceReadOnlyIterationWithoutCopying) {
  std::vector<int> values{1, 2, 3};
  auto first = std::cbegin(values);

  static_assert(std::is_same_v<decltype(*first), const int&>);
  EXPECT_EQ(first, values.cbegin());
  EXPECT_EQ(std::cend(values), values.cend());

  values[0] = 10;
  EXPECT_EQ(*first, 10);

  // cbegin/cend 接受 const C& 视图并返回只读 iterator；它们不复制或冻结容器，
  // 因此通过其他合法别名修改元素后，iterator 仍观察同一对象的新值。
}

TEST(RangeAccess, ReverseAccessStartsFromTheLastElement) {
  int values[] = {1, 2, 3, 4};
  auto first = std::rbegin(values);
  auto last = std::rend(values);

  static_assert(std::is_same_v<decltype(first), std::reverse_iterator<int*>>);
  EXPECT_EQ(*first, 4);
  EXPECT_EQ(std::distance(first, last), 4);

  const auto& readonly = values;
  static_assert(std::is_same_v<
                decltype(std::crbegin(readonly)),
                std::reverse_iterator<const int*>>);

  // rbegin(array) 等价于 reverse_iterator(array+N)，rend 对应 array；const 版本保留
  // 元素限定。其 base() 仍遵守 reverse_iterator 的错一位关系。
}

TEST(RangeAccess, SizeAndSsizeReturnUnsignedAndSignedCountsForDifferentUses) {
  std::array<int, 4> values{1, 2, 3, 4};
  int raw[] = {5, 6, 7};

  static_assert(std::is_unsigned_v<decltype(std::size(values))>);
  static_assert(std::is_signed_v<decltype(std::ssize(values))>);
  static_assert(std::is_same_v<decltype(std::ssize(raw)), std::ptrdiff_t>);

  EXPECT_EQ(std::size(values), 4U);
  EXPECT_EQ(std::ssize(values) - 5, -1);
  EXPECT_EQ(std::size(raw), 3U);

  // size 通常返回无符号 size_type，`size()-5` 在小容器上会下溢；C++20 ssize 返回
  // 能表示 ptrdiff_t 与容器 size 的公共有符号类型，适合差值和倒序索引计算。
}

TEST(RangeAccess, EmptySupportsContainersArraysAndInitializerLists) {
  std::vector<int> container;
  int raw[] = {1};

  EXPECT_TRUE(std::empty(container));
  EXPECT_FALSE(std::empty(raw));
  EXPECT_TRUE(std::empty(std::initializer_list<int>{}));
  EXPECT_FALSE(std::empty({1, 2}));

  // 内建 C++ 数组的 N 必须大于 0，所以 std::empty(raw) 恒为 false；空数组不是标准
  // 内建数组类型。initializer_list 有专门 overload，容器则转发 empty()。
}

TEST(RangeAccess, DataReturnsTheFirstContiguousAddressButDoesNotProveALifetime) {
  std::vector<int> container{1, 2, 3};
  int raw[] = {4, 5, 6};
  std::initializer_list<int> listed{7, 8, 9};

  EXPECT_EQ(std::data(container), container.data());
  EXPECT_EQ(std::data(raw), &raw[0]);
  EXPECT_EQ(std::data(listed), listed.begin());
  EXPECT_EQ(*std::data(listed), 7);

  // std::data 只统一取得连续起始地址，不携带长度或所有权。initializer_list 的 backing
  // array 寿命跟随该 initializer_list 对象；从临时列表保存 data 指针会很快悬空。
}

TEST(RangeAccess, UsingStdThenUnqualifiedCallAddsAdlCustomization) {
  adl_buffer::Buffer custom{{2, 3, 5}};
  std::array<int, 3> standard{7, 11, 13};

  EXPECT_EQ(SumWithAdl(custom), 10);
  EXPECT_EQ(SumWithAdl(standard), 31);

  // `using std::begin; begin(range)` 同时保留标准 overload 与参数关联命名空间中的自由
  // begin/end。直接写 std::begin(custom) 只查 std overload，不会执行 ADL。
}

TEST(RangeAccess, InitializerListPointersMustNotEscapeTheOwningListLifetime) {
  auto inspect_now = [](std::initializer_list<int> values) {
    return std::pair{std::size(values), *std::data(values)};
  };

  const auto result = inspect_now({3, 4, 5});
  EXPECT_EQ(result.first, 3U);
  EXPECT_EQ(result.second, 3);

  // 临时 initializer_list 的 backing array 只活到包含调用的 full-expression 结束。
  // lambda 在调用内复制值是安全的；若返回 data()/begin() 指针，调用结束后就会悬空。
}

}  // namespace
