// polyglot-covers:
// - cpp.stdlib.iterators.move-iterator-rvalue-dereference
// - cpp.stdlib.iterators.make-move-iterator-and-moving-range-construction
// - cpp.stdlib.iterators.move-iterator-base-and-navigation
// - cpp.stdlib.iterators.move-iterator-does-not-itself-move
// - cpp.stdlib.iterators.move-iterator-concept-version-evolution
// - cpp.stdlib.iterators.move-iterator-mutable-to-const-conversion
// - cpp.stdlib.iterators.move-sentinel-different-end-type
// - cpp.stdlib.iterators.move-iterator-iter-swap-forwarding

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <iterator>
#include <memory>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(MoveIterator, DereferencePresentsTheUnderlyingElementAsAnRvalue) {
  std::vector<std::unique_ptr<int>> source;
  source.push_back(std::make_unique<int>(7));
  source.push_back(std::make_unique<int>(11));

  using Base = decltype(source.begin());
  using Moved = std::move_iterator<Base>;
  static_assert(std::is_same_v<decltype(*Moved{source.begin()}),
                               std::unique_ptr<int>&&>);

  std::vector<std::unique_ptr<int>> destination(
      std::make_move_iterator(source.begin()),
      std::make_move_iterator(source.end()));

  ASSERT_EQ(destination.size(), 2U);
  EXPECT_EQ(*destination[0], 7);
  EXPECT_EQ(*destination[1], 11);
  EXPECT_EQ(source[0], nullptr);
  EXPECT_EQ(source[1], nullptr);

  // move_iterator 让读取表达式产生 iter_rvalue_reference_t，接收容器因而调用移动构造。
  // 源容器仍有两个元素，只是 unique_ptr 所有权已转移；移动不会自动 erase 源元素。
}

TEST(MoveIterator, CreatingOrDereferencingItDoesNotConsumeTheValueByItself) {
  std::string source = "payload";
  auto iterator = std::make_move_iterator(&source);

  auto&& rvalue_reference = *iterator;
  EXPECT_EQ(source, "payload");
  EXPECT_EQ(rvalue_reference, "payload");

  std::string destination = std::move(rvalue_reference);
  EXPECT_EQ(destination, "payload");

  // 与 std::move 一样，适配器只改变值类别；真正由接收方构造/赋值时才发生移动。
  // 移动后的 source 仍有效但状态未指定，本例不要求它一定为空。
}

TEST(MoveIterator, BaseAndNavigationTrackTheSamePositionWithoutOffset) {
  std::array<std::string, 4> values{"a", "b", "c", "d"};
  auto first = std::make_move_iterator(values.begin());
  auto third = first + 2;

  EXPECT_EQ(first.base(), values.begin());
  EXPECT_EQ(third.base(), values.begin() + 2);
  EXPECT_EQ(*third, "c");
  EXPECT_EQ(third - first, 2);
  EXPECT_EQ(third[1], "d");

  // move_iterator 与 reverse_iterator 不同：base() 就是同一逻辑位置，没有错一位。
  // 导航和比较转发给底层 iterator，只有解引用改用 ranges::iter_move。
}

TEST(MoveIterator, ConceptMetadataRecordsTheCxx20ToLaterStandardEvolution) {
  using Base = std::vector<int>::iterator;
  using Moved = std::move_iterator<Base>;
  using Concept = typename Moved::iterator_concept;

  static_assert(std::input_iterator<Moved>);
  static_assert(std::is_same_v<
                typename std::iterator_traits<Moved>::iterator_category,
                std::random_access_iterator_tag>);
  static_assert(requires(Moved iterator) {
    iterator + 2;
    iterator[1];
  });

  if constexpr (std::is_same_v<Concept, std::input_iterator_tag>) {
    EXPECT_FALSE(std::forward_iterator<Moved>);
  } else {
    EXPECT_TRUE(std::random_access_iterator<Moved>);
  }

  // 锁定的 N4861 把 iterator_concept 固定为 input_iterator_tag，legacy category 仍可
  // 是 random access；后续标准修订改为按底层概念保留最强层级，部分实现会回溯该修订。
  // 因此代码应按特性检测，不能用编译器版本猜测 ranges 算法会接受哪一层概念。
}

TEST(MoveIterator, MutableBaseConvertsToConstBaseButNotConversely) {
  std::vector<std::string> values{"a", "b"};
  using Mutable = std::move_iterator<std::vector<std::string>::iterator>;
  using Readonly = std::move_iterator<std::vector<std::string>::const_iterator>;

  static_assert(std::is_constructible_v<Readonly, Mutable>);
  static_assert(!std::is_constructible_v<Mutable, Readonly>);

  Mutable mutable_first{values.begin()};
  Readonly readonly_first = mutable_first;
  EXPECT_EQ(*readonly_first, "a");

  // 适配器转换依赖底层 iterator 的转换。const 基础迭代器的 iter_move 产生 const T&&，
  // 通常无法调用只接受 T&& 的高效移动构造，可能退化为复制。
}

TEST(MoveSentinel, ItPairsAMovedIteratorWithADifferentSentinelType) {
  std::array<std::unique_ptr<int>, 2> source{
      std::make_unique<int>(3),
      std::make_unique<int>(5),
  };
  std::move_iterator first{source.begin()};
  std::move_sentinel last{source.end()};

  static_assert(std::sentinel_for<decltype(last), decltype(first)>);
  static_assert(std::sized_sentinel_for<decltype(last), decltype(first)>);
  EXPECT_EQ(last - first, 2);

  std::vector<std::unique_ptr<int>> destination;
  for (; first != last; ++first) {
    destination.push_back(*first);
  }

  ASSERT_EQ(destination.size(), 2U);
  EXPECT_EQ(*destination[0], 3);
  EXPECT_EQ(*destination[1], 5);
  EXPECT_EQ(source[0], nullptr);
  EXPECT_EQ(source[1], nullptr);

  // move_sentinel 包装原 sentinel，使它能和 move_iterator 比较/求距；当 range 的 end
  // 与 iterator 类型不同，就不必伪造一个 move_iterator<Sentinel>。
}

TEST(MoveIterator, IterSwapStillSwapsTheUnderlyingLogicalElements) {
  std::array<std::string, 2> values{"left", "right"};
  auto left = std::make_move_iterator(values.begin());
  auto right = std::make_move_iterator(values.begin() + 1);

  std::ranges::iter_swap(left, right);

  EXPECT_EQ(values, (std::array<std::string, 2>{"right", "left"}));

  // move_iterator 的 iter_swap 转发到 ranges::iter_swap(base1,base2)，而不是先把两个值
  // 移到临时容器。这样底层 iterator 的代理引用与 ADL 定制仍能参与。
}

}  // namespace
