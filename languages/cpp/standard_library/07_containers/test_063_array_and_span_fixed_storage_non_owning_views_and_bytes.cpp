// polyglot-covers:
// - cpp.stdlib.containers.array-aggregate-initialization-and-fixed-size
// - cpp.stdlib.containers.array-contiguous-access-and-bounds
// - cpp.stdlib.containers.array-fill-swap-and-comparison
// - cpp.stdlib.containers.array-tuple-interface
// - cpp.stdlib.containers.to-array-copy-move-and-string-terminator
// - cpp.stdlib.containers.zero-length-array
// - cpp.stdlib.containers.span-static-and-dynamic-extent
// - cpp.stdlib.containers.span-non-owning-mutation-and-const-conversion
// - cpp.stdlib.containers.span-subviews-and-size-bytes
// - cpp.stdlib.containers.span-as-bytes-and-as-writable-bytes
// - cpp.stdlib.containers.span-borrowed-range-and-lifetime

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <memory>
#include <ranges>
#include <span>
#include <stdexcept>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(Array, AggregateInitializationKeepsTheSizeInTheType) {
  std::array<int, 4> values{1, 2};
  std::array<int, 4> zeros{};

  EXPECT_EQ(values, (std::array<int, 4>{1, 2, 0, 0}));
  EXPECT_EQ(zeros, (std::array<int, 4>{0, 0, 0, 0}));
  static_assert(std::tuple_size_v<decltype(values)> == 4);
  static_assert(!std::is_same_v<std::array<int, 3>, std::array<int, 4>>);

  // array 是聚合且 N 是类型的一部分；列表中未给出的后续元素会值初始化。
  // 不带花括号的默认初始化 `std::array<int, 4> raw;` 会留下不确定 int，读取前必须写入。
}

TEST(Array, IteratorsAndDataDescribeOneContiguousRange) {
  std::array<int, 4> values{3, 5, 7, 11};

  EXPECT_EQ(values.data(), &values.front());
  EXPECT_EQ(values.data() + values.size(), values.end());
  EXPECT_EQ(values.back(), 11);
  EXPECT_EQ(values[2], 7);
  EXPECT_THROW((void)values.at(values.size()), std::out_of_range);

  values.at(1) = 13;
  EXPECT_EQ(values[1], 13);

  // array 满足 contiguous container，data()+size() 对应 end()。at() 越界抛异常，
  // operator[]、front() 和 back() 都依赖调用者的有效索引/非空前置条件，不会回退到默认值。
}

TEST(Array, FillSwapAndComparisonOperateElementByElement) {
  std::array<int, 3> first;
  first.fill(4);
  std::array<int, 3> second{4, 4, 5};

  EXPECT_LT(first, second);
  first.swap(second);
  EXPECT_EQ(first, (std::array<int, 3>{4, 4, 5}));
  EXPECT_EQ(second, (std::array<int, 3>{4, 4, 4}));

  // array::swap 交换 N 个元素，复杂度是线性，不能像 vector 那样只交换
  // 三个管理字段。比较是字典序，在第一个不等元素处决定结果。
}

TEST(Array, TupleInterfaceProvidesCompileTimeIndexedAccess) {
  std::array<std::string, 2> names{"Ada", "Bjarne"};
  auto& [first, second] = names;

  static_assert(
      std::is_same_v<std::tuple_element_t<0, decltype(names)>, std::string>);
  EXPECT_EQ(std::get<0>(names), "Ada");

  second = "Dennis";
  EXPECT_EQ(names[1], "Dennis");
  EXPECT_EQ(&first, &names[0]);

  // array 专门提供 tuple_size、tuple_element 和 get<I>，所以可用结构化绑定。
  // get<I> 的 I 是编译期常量；运行期索引仍应使用 [] 或 at()。
}

TEST(ToArray, CopiesLvaluesMovesRvaluesAndKeepsStringTerminators) {
  int raw_values[] = {2, 3, 5};
  const auto copied = std::to_array(raw_values);
  raw_values[0] = 99;
  EXPECT_EQ(copied, (std::array<int, 3>{2, 3, 5}));

  std::unique_ptr<int> raw_owners[] = {
      std::make_unique<int>(7),
      std::make_unique<int>(11),
  };
  auto moved = std::to_array(std::move(raw_owners));
  EXPECT_EQ(*moved[0], 7);
  EXPECT_EQ(raw_owners[0], nullptr);

  constexpr auto text = std::to_array("hi");
  static_assert(text.size() == 3);
  static_assert(text[2] == '\0');

  // to_array 从内建数组推导 N，lvalue 版本复制元素，rvalue 数组版本移动元素。
  // 字符串字面量的内建数组包含结尾 '\0'，因此 to_array("hi") 的长度是 3 而非 2。
}

TEST(Array, ZeroLengthArrayHasNoFrontOrBackElement) {
  std::array<int, 0> empty{};

  EXPECT_TRUE(empty.empty());
  EXPECT_EQ(empty.size(), 0U);
  EXPECT_EQ(empty.begin(), empty.end());

  // array<T, 0> 是有效容器，begin()==end()。data() 的具体空指针表示不应被
  // 依赖，front()/back() 更没有可访问元素；不要为统一代码路径而解引用空 array。
}

TEST(Span, StaticAndDynamicExtentsAreDifferentTypesOverTheSameStorage) {
  int values[] = {1, 2, 3, 4};
  std::span fixed{values};
  std::span<int> dynamic{values};

  static_assert(std::is_same_v<decltype(fixed), std::span<int, 4>>);
  static_assert(decltype(fixed)::extent == 4);
  static_assert(decltype(dynamic)::extent == std::dynamic_extent);
  EXPECT_EQ(fixed.data(), dynamic.data());
  EXPECT_EQ(dynamic.size(), 4U);

  std::span<int, 4> checked_static{dynamic};
  EXPECT_EQ(checked_static.data(), values);

  // 静态 extent 进入 span 类型，动态 extent 则在对象中保存 size。从 dynamic span
  // 直接构造静态 span 时，调用者必须保证运行期 size 恰好等于 Extent，否则违反前置条件。
}

TEST(Span, MutabilityBelongsToElementTypeNotToTheSpanObjectConstness) {
  std::array<int, 3> values{3, 4, 5};
  const std::span<int> mutable_elements{values};
  const std::span<const int> readonly_elements{values};

  mutable_elements[1] = 40;
  EXPECT_EQ(values[1], 40);
  EXPECT_EQ(readonly_elements[1], 40);
  static_assert(
      std::is_same_v<decltype(mutable_elements[0]), int&>);
  static_assert(
      std::is_same_v<decltype(readonly_elements[0]), const int&>);

  // const span<int> 只表示 view 的指针/长度不可重绑定，元素仍是 int&。
  // 只有 span<const int> 才禁止通过 view 写入，且它可从可变存储安全转换而来。
}

TEST(Span, SubviewsPreserveStaticExtentWhenTheArgumentsAreCompileTimeValues) {
  std::array<int, 6> values{0, 1, 2, 3, 4, 5};
  std::span<int, 6> all{values};

  auto first = all.first<2>();
  auto middle = all.subspan<2, 3>();
  auto runtime_tail = all.last(2);

  static_assert(std::is_same_v<decltype(first), std::span<int, 2>>);
  static_assert(std::is_same_v<decltype(middle), std::span<int, 3>>);
  static_assert(
      std::is_same_v<decltype(runtime_tail), std::span<int, std::dynamic_extent>>);
  EXPECT_EQ(middle[0], 2);
  EXPECT_EQ(middle[2], 4);
  EXPECT_EQ(runtime_tail[0], 4);
  EXPECT_EQ(all.size_bytes(), all.size() * sizeof(int));

  // 模板 subview 把 Count 保留在返回类型中，运行期 count overload 只能返回
  // dynamic_extent。所有 first/last/subspan 都不做分配或复制，并要求边界在原 span 之内。
}

TEST(Span, ByteViewsExposeObjectRepresentationWithoutTakingOwnership) {
  std::array<unsigned char, 3> values{1, 2, 3};
  std::span<unsigned char> elements{values};
  auto readonly_bytes = std::as_bytes(elements);
  auto writable_bytes = std::as_writable_bytes(elements);

  static_assert(
      std::is_same_v<decltype(readonly_bytes)::element_type, const std::byte>);
  static_assert(
      std::is_same_v<decltype(writable_bytes)::element_type, std::byte>);
  EXPECT_EQ(readonly_bytes.size(), values.size());

  writable_bytes[1] = std::byte{0x7f};
  EXPECT_EQ(values[1], 0x7f);

  // as_bytes 总返回 const byte view，as_writable_bytes 只接受非 const 元素。它们展开
  // 对象表示但不改变存储寿命；随意改普通类型的字节可产生陷阱表示，本例仅修改 unsigned char。
}

TEST(Span, BorrowedRangeStatusDoesNotMakeTemporaryOwnedStorageLiveLonger) {
  static_assert(std::ranges::borrowed_range<std::span<int>>);
  static_assert(
      std::is_constructible_v<std::span<const int>, std::vector<int>&&>);
  static_assert(
      !std::is_constructible_v<std::span<int>, std::vector<int>&&>);

  // span 是 borrowed_range，因为移动 span 不会使其 iterator 失效；这不代表它延长
  // 底层容器寿命。span<const T> 可从临时 contiguous range 构造，但 full-expression 结束就悬空，不应存储。
}

}  // namespace
