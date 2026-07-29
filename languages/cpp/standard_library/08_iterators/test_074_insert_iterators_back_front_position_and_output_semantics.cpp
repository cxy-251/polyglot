// polyglot-covers:
// - cpp.stdlib.iterators.back-insert-iterator-and-back-inserter
// - cpp.stdlib.iterators.front-insert-iterator-and-front-inserter
// - cpp.stdlib.iterators.insert-iterator-and-inserter
// - cpp.stdlib.iterators.insert-iterator-assignment-invokes-container-operation
// - cpp.stdlib.iterators.front-inserter-reverses-sequential-assignment-order
// - cpp.stdlib.iterators.position-inserter-preserves-sequential-assignment-order
// - cpp.stdlib.iterators.insert-iterators-as-write-only-output-iterators
// - cpp.stdlib.iterators.copy-to-growing-container-without-preallocation

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <deque>
#include <iterator>
#include <list>
#include <memory>
#include <set>
#include <vector>

namespace {

TEST(BackInsertIterator, AssignmentCallsPushBackAndGrowthIsHandledByTheContainer) {
  std::vector<int> destination{1};
  auto output = std::back_inserter(destination);

  *output = 2;
  ++output;
  output++;
  *output = 3;

  EXPECT_EQ(destination, (std::vector<int>{1, 2, 3}));

  // 对 back_insert_iterator 的 `*out=value` 实际调用 container.push_back(value)；
  // operator* 与 ++ 只返回自身。它不指向既有元素，容器扩容也无需修复 output。
}

TEST(BackInsertIterator, CopyCanGrowAnInitiallyEmptyDestinationSafely) {
  const std::array<int, 4> source{2, 3, 5, 7};
  std::vector<int> destination;

  std::copy(source.begin(), source.end(), std::back_inserter(destination));

  EXPECT_EQ(destination, (std::vector<int>{2, 3, 5, 7}));

  // 把 destination.begin() 作为输出位置时必须先 resize 到足够大小；reserve 只分配容量，
  // 不能使解引用 begin() 合法。back_inserter 让算法通过 push_back 正确增长 size。
}

TEST(FrontInsertIterator, RepeatedFrontInsertionReversesTheSourceOrder) {
  const std::array<int, 4> source{1, 2, 3, 4};
  std::deque<int> destination;

  std::copy(source.begin(), source.end(), std::front_inserter(destination));

  EXPECT_EQ(destination, (std::deque<int>{4, 3, 2, 1}));

  // 每次赋值都调用 push_front，新值放在上一个值之前，所以顺序反转。若希望最终顺序
  // 与 source 相同，可以反向遍历 source，或选择合适的 back/position inserter。
}

TEST(InsertIterator, ItAdvancesItsStoredPositionAfterEachInsertion) {
  std::list<int> destination{1, 5};
  const std::array<int, 3> middle{2, 3, 4};
  auto position = std::next(destination.begin());

  std::copy(middle.begin(), middle.end(), std::inserter(destination, position));

  EXPECT_EQ(destination, (std::list<int>{1, 2, 3, 4, 5}));

  // insert_iterator 执行 `position = container.insert(position, value); ++position`，
  // 因而连续赋值保持 source 顺序，而不是总在同一位置前插导致反转。
}

TEST(InsertIterator, GenericInserterAlsoWorksWithUniqueAssociativeContainers) {
  const std::array<int, 5> source{3, 1, 2, 3, 2};
  std::set<int> destination;

  std::copy(source.begin(), source.end(), std::inserter(destination, destination.end()));

  EXPECT_EQ(destination, (std::set<int>{1, 2, 3}));

  // inserter 使用容器的 insert(pos,value) 形式，set 把 pos 当提示并自行维护排序与唯一性。
  // 重复输入不会报错，也不会在输出迭代器中暴露 inserted bool。
}

TEST(InsertIterators, TheyAreWritableOutputIteratorsButNotReadableIterators) {
  using Back = std::back_insert_iterator<std::vector<int>>;
  using Front = std::front_insert_iterator<std::deque<int>>;
  using Position = std::insert_iterator<std::list<int>>;

  static_assert(std::output_iterator<Back, int>);
  static_assert(std::output_iterator<Front, int>);
  static_assert(std::output_iterator<Position, int>);
  static_assert(!std::input_iterator<Back>);
  static_assert(!std::indirectly_readable<Back>);

  // 它们的 value_type/reference 常为 void，*out 不代表一个可读取元素；只应出现在
  // 算法输出端。把“可解引用表达式存在”误当成“可读”会写出错误的泛型约束。
}

TEST(InsertIterators, MoveAssignmentTransfersMoveOnlyValuesIntoTheContainer) {
  std::vector<std::unique_ptr<int>> destination;
  auto output = std::back_inserter(destination);
  auto owner = std::make_unique<int>(7);

  *output = std::move(owner);

  EXPECT_EQ(owner, nullptr);
  ASSERT_EQ(destination.size(), 1U);
  EXPECT_EQ(*destination.front(), 7);

  // output 赋值有 const T& 与 T&& 路径，rvalue 会传给 push_back/insert 的移动 overload。
  // 适配器自身仍不拥有值；所有权最终属于目标容器。
}

}  // namespace
