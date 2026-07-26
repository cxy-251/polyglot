// polyglot-covers:
// - cpp.stdlib.iterators.reverse-iterator-construction-from-end
// - cpp.stdlib.iterators.reverse-iterator-base-off-by-one-invariant
// - cpp.stdlib.iterators.reverse-iterator-navigation-direction
// - cpp.stdlib.iterators.reverse-iterator-comparison-reversal
// - cpp.stdlib.iterators.reverse-iterator-mutable-to-const-conversion
// - cpp.stdlib.iterators.make-reverse-iterator
// - cpp.stdlib.iterators.reverse-iterator-iter-move-and-iter-swap
// - cpp.stdlib.iterators.reverse-iterator-underlying-invalidation

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <iterator>
#include <ranges>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(ReverseIterator, ConstructingFromEndMakesTheLastElementFirst) {
  std::array<int, 4> values{1, 2, 3, 4};
  std::reverse_iterator last_first{values.end()};
  std::reverse_iterator before_first{values.begin()};

  EXPECT_EQ(*last_first, 4);
  EXPECT_EQ(last_first.base(), values.end());

  std::vector<int> reversed(last_first, before_first);
  EXPECT_EQ(reversed, (std::vector<int>{4, 3, 2, 1}));

  // reverse_iterator 保存的 current 指向“反向元素之后”的正向位置，解引用等价于
  // *prev(current)。因此从 end 构造后首先看到最后元素，从 begin 构造的是反向末尾。
}

TEST(ReverseIterator, BasePointsOnePositionAfterTheDereferencedElement) {
  std::vector<int> values{1, 2, 3, 4};
  auto reversed_three = std::find(values.rbegin(), values.rend(), 3);
  ASSERT_NE(reversed_three, values.rend());

  auto forward_three = std::prev(reversed_three.base());
  EXPECT_EQ(*forward_three, 3);

  auto following = values.erase(forward_three);
  EXPECT_EQ(*following, 4);
  EXPECT_EQ(values, (std::vector<int>{1, 2, 4}));

  // `&*r == &*prev(r.base())` 是核心不变量。直接 erase(r.base()) 会删除反向所指元素
  // 的正向后继，甚至在 r 指向最后元素时把 end() 交给 erase。
}

TEST(ReverseIterator, IncrementAndArithmeticMoveInTheOppositeBaseDirection) {
  std::array<int, 5> values{1, 2, 3, 4, 5};
  auto iterator = values.rbegin();

  ++iterator;
  EXPECT_EQ(*iterator, 4);
  EXPECT_EQ(iterator.base(), values.end() - 1);

  iterator += 2;
  EXPECT_EQ(*iterator, 2);
  EXPECT_EQ(iterator[1], 1);

  // 反向 ++ 会对 base 执行 --，r+n 对应 base-n；operator[] 也沿反向序列取值。
  // 算法看到的是正常随机访问接口，但方向翻转封装在适配器内部。
}

TEST(ReverseIterator, OrderingIsReversedRelativeToTheBaseIterators) {
  std::array<int, 4> values{1, 2, 3, 4};
  auto first = values.rbegin();
  auto second = first + 1;

  EXPECT_LT(first, second);
  EXPECT_GT(first.base(), second.base());
  EXPECT_EQ(second - first, 1);

  // 为使反向 range 仍按遍历方向递增，reverse_iterator 的关系比较交换 base 两边；
  // 距离 `y-x` 也换算成 `x.base()-y.base()`。
}

TEST(ReverseIterator, MutableIteratorConvertsToItsConstCounterpart) {
  std::vector<std::string> values{"a", "b"};
  using Mutable = std::vector<std::string>::reverse_iterator;
  using Readonly = std::vector<std::string>::const_reverse_iterator;

  static_assert(std::is_constructible_v<Readonly, Mutable>);
  static_assert(!std::is_constructible_v<Mutable, Readonly>);

  Mutable mutable_last = values.rbegin();
  Readonly readonly_last = mutable_last;
  EXPECT_EQ(*readonly_last, "b");

  // conversion 是否可用取决于底层 iterator 的可转换方向；可变到 const 安全，
  // const 到可变会丢限定，因而被拒绝。
}

TEST(ReverseIterator, FactoryDeducesTheUnderlyingIteratorType) {
  int values[] = {2, 3, 5};
  auto iterator = std::make_reverse_iterator(std::end(values));

  static_assert(std::is_same_v<decltype(iterator), std::reverse_iterator<int*>>);
  EXPECT_EQ(*iterator, 5);

  // make_reverse_iterator 在 C++14 起省去显式模板参数；工厂参数仍是正向的“元素之后”
  // iterator，通常传 end 而不是 last element。
}

TEST(ReverseIterator, IterMoveAndIterSwapTargetTheLogicalReverseElements) {
  std::array<std::string, 2> values{"first", "last"};
  auto last = values.rbegin();
  auto first = last + 1;

  static_assert(std::is_same_v<
                decltype(std::ranges::iter_move(last)),
                std::string&&>);
  std::ranges::iter_swap(last, first);

  EXPECT_EQ(values, (std::array<std::string, 2>{"last", "first"}));

  // reverse_iterator 把 iter_move/iter_swap 转发到 prev(base()) 所指元素，保留底层
  // iterator 的代理或 ADL 定制语义，而不是简单对适配器对象本身交换。
}

TEST(ReverseIterator, ItSharesTheUnderlyingContainersInvalidationRules) {
  std::vector<int> values{1, 2, 3};
  values.reserve(values.capacity() + 5);

  auto fresh = values.rbegin();
  EXPECT_EQ(*fresh, 3);

  // 扩容前取得的任何 reverse_iterator 都包装旧 vector iterator，同样会全部失效。
  // 适配器不拥有元素，也不会使 handle 更稳定；本例只在 reserve 之后创建 fresh。
}

}  // namespace
