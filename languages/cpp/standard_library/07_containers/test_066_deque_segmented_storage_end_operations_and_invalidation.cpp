// polyglot-covers:
// - cpp.stdlib.containers.deque-double-ended-growth-and-random-access
// - cpp.stdlib.containers.deque-segmented-non-contiguous-storage
// - cpp.stdlib.containers.deque-end-insertion-reference-stability
// - cpp.stdlib.containers.deque-middle-insertion-and-erasure-invalidation
// - cpp.stdlib.containers.deque-pop-and-erase-return-values
// - cpp.stdlib.containers.deque-resize-shrink-and-free-erase
// - cpp.stdlib.containers.deque-move-only-elements

#include <gtest/gtest.h>

#include <concepts>
#include <deque>
#include <memory>
#include <ranges>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace {

template <class Container>
concept HasDataMember = requires(Container& container) {
  container.data();
};

TEST(Deque, BothEndsGrowEfficientlyAndElementsRemainRandomAccess) {
  std::deque<int> values{2, 3};

  values.push_front(1);
  values.emplace_front(0);
  values.push_back(4);
  int& last = values.emplace_back(5);

  EXPECT_EQ(values, (std::deque<int>{0, 1, 2, 3, 4, 5}));
  EXPECT_EQ(&last, &values.back());
  EXPECT_EQ(values[3], 3);
  EXPECT_THROW((void)values.at(6), std::out_of_range);

  // deque 在两端插入/删除具有常数复杂度，并保留随机访问。与 vector 相比，
  // 它不需要为头部增长整体搬移元素；at() 与 [] 的边界检查差异相同。
}

TEST(Deque, RandomAccessDoesNotImplyContiguousStorage) {
  using Values = std::deque<int>;

  static_assert(std::ranges::random_access_range<Values>);
  static_assert(!std::ranges::contiguous_range<Values>);
  static_assert(!HasDataMember<Values>);

  Values values(2000, 7);
  EXPECT_EQ(values.end() - values.begin(), 2000);
  EXPECT_EQ(values[1999], 7);

  // deque 通常由映射表连接多个固定大小块；iterator 能做常数时间 +/-，却没有
  // 覆盖全部元素的单一 data() 指针。不能把 &front() 和 size 当作连续数组传出。
}

TEST(Deque, EndInsertionPreservesElementReferencesButInvalidatesIterators) {
  std::deque<int> values{2, 3, 4};
  int& middle = values[1];
  int* middle_address = &values[1];

  values.push_front(1);
  values.push_back(5);

  EXPECT_EQ(middle, 3);
  EXPECT_EQ(middle_address, &values[2]);
  EXPECT_EQ(values, (std::deque<int>{1, 2, 3, 4, 5}));

  // 在任一端插入不会让既有元素的 reference/pointer 失效，这是 deque 的重要用途；
  // 但 iterator（包括旧 end）会失效。这里故意不保存或继续使用插入前的 iterator。
}

TEST(Deque, MiddleInsertionMayInvalidateEveryHandle) {
  std::deque<int> values{1, 2, 4, 5};

  auto inserted = values.insert(values.begin() + 2, 3);

  EXPECT_EQ(*inserted, 3);
  EXPECT_EQ(values, (std::deque<int>{1, 2, 3, 4, 5}));

  // 中间 insert/emplace 会搬移一侧元素，所有 iterator 和 reference 都可能失效。
  // 不应因 deque 的“端点引用稳定”就把同一保证推广到任意插入位置。
}

TEST(Deque, EraseReturnsTheElementAfterTheRemovedRange) {
  std::deque<int> values{1, 2, 3, 4, 5};

  auto following = values.erase(values.begin() + 1, values.begin() + 4);

  EXPECT_EQ(values, (std::deque<int>{1, 5}));
  ASSERT_NE(following, values.end());
  EXPECT_EQ(*following, 5);

  values.pop_front();
  values.pop_back();
  EXPECT_TRUE(values.empty());

  // erase 返回新区间中紧随删除部分的位置。pop_front/pop_back 不返回元素，且要求
  // 容器非空；如果需要取走值，应在 pop 之前复制或移动 front()/back()。
}

TEST(Deque, ResizeFreeEraseAndShrinkHaveTheExpectedSeparateEffects) {
  std::deque<int> values{1, 2, 2, 3, 4, 2};

  const auto removed = std::erase(values, 2);
  EXPECT_EQ(removed, 3U);
  EXPECT_EQ(values, (std::deque<int>{1, 3, 4}));

  values.resize(5, 9);
  EXPECT_EQ(values, (std::deque<int>{1, 3, 4, 9, 9}));

  values.resize(2);
  values.shrink_to_fit();
  EXPECT_EQ(values, (std::deque<int>{1, 3}));

  // C++20 std::erase 返回删除数量。resize 改变逻辑元素数；shrink_to_fit 只是请求
  // 减少未使用内存且不会改变值，标准不保证具体块数或是否真的归还内存。
}

TEST(Deque, MoveOnlyValuesCanBeTransferredBeforePopping) {
  std::deque<std::unique_ptr<int>> owners;
  owners.emplace_front(std::make_unique<int>(7));
  owners.emplace_back(std::make_unique<int>(11));

  auto first = std::move(owners.front());
  owners.pop_front();

  EXPECT_EQ(*first, 7);
  ASSERT_EQ(owners.size(), 1U);
  EXPECT_EQ(*owners.front(), 11);

  // 与 vector 一样，deque 可以保存 move-only 元素。pop 不负责把值返回给调用者，
  // 先移动再 pop 才能明确转移所有权，且避免保留已被销毁元素的引用。
}

}  // namespace
