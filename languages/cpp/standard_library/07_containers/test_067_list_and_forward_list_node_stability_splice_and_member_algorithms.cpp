// polyglot-covers:
// - cpp.stdlib.containers.list-bidirectional-node-container
// - cpp.stdlib.containers.list-stable-references-and-iterators
// - cpp.stdlib.containers.list-splice-without-element-moves
// - cpp.stdlib.containers.list-sort-merge-unique-and-remove
// - cpp.stdlib.containers.list-insert-erase-and-return-values
// - cpp.stdlib.containers.forward-list-before-begin-and-after-operations
// - cpp.stdlib.containers.forward-list-no-size-and-forward-iteration
// - cpp.stdlib.containers.forward-list-splice-sort-merge-remove-and-reverse

#include <gtest/gtest.h>

#include <concepts>
#include <forward_list>
#include <iterator>
#include <list>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>

namespace {

template <class Container>
concept HasSizeMember = requires(const Container& container) {
  container.size();
};

TEST(List, BidirectionalNodesTradeRandomAccessForStableHandles) {
  std::list<int> values{2, 3, 4};
  auto middle = std::next(values.begin());
  int& middle_reference = *middle;
  int* middle_address = &*middle;

  values.push_front(1);
  values.push_back(5);
  values.insert(middle, 20);

  static_assert(std::ranges::bidirectional_range<decltype(values)>);
  static_assert(!std::ranges::random_access_range<decltype(values)>);
  EXPECT_EQ(middle_reference, 3);
  EXPECT_EQ(middle_address, &*middle);
  EXPECT_EQ(values, (std::list<int>{1, 2, 20, 3, 4, 5}));

  // list 的每个元素在独立节点中，插入不会移动既有节点，所以 iterator/reference
  // 保持有效；代价是不能用 [] 或 iterator+n 随机访问，并有节点分配与指针开销。
}

TEST(List, EraseInvalidatesOnlyRemovedNodesAndReturnsTheFollowingIterator) {
  std::list<int> values{1, 2, 3, 4};
  auto first = values.begin();
  auto two = std::next(first);
  auto three = std::next(two);

  auto following = values.erase(two);

  EXPECT_EQ(*first, 1);
  EXPECT_EQ(following, three);
  EXPECT_EQ(*following, 3);
  EXPECT_EQ(values, (std::list<int>{1, 3, 4}));

  // erase 只让被删除节点的 handle 失效，其他节点的 iterator/reference 不变。
  // 返回值指向删除位置之后的节点；删除末元素时返回 end()。
}

TEST(List, SpliceRelinksNodesWithoutCopyingOrMovingTheirValues) {
  std::list<std::string> ready{"compile", "test"};
  std::list<std::string> pending{"review", "commit"};
  auto review = pending.begin();
  std::string* review_address = &*review;

  ready.splice(ready.begin(), pending, review);

  EXPECT_EQ(ready, (std::list<std::string>{"review", "compile", "test"}));
  EXPECT_EQ(pending, (std::list<std::string>{"commit"}));
  EXPECT_EQ(review_address, &ready.front());
  EXPECT_EQ(*review, "review");

  // allocator 兼容时，splice 只重连节点，元素本身不复制、不移动，原 iterator/reference
  // 继续指向同一对象，只是它现在属于另一个容器。allocator 不同则违反前置条件。
}

TEST(List, SortMergeUniqueAndRemoveAreNodeAwareMemberAlgorithms) {
  std::list<int> odd{5, 1, 3};
  std::list<int> even{6, 2, 4};

  odd.sort();
  even.sort();
  odd.merge(even);

  EXPECT_EQ(odd, (std::list<int>{1, 2, 3, 4, 5, 6}));
  EXPECT_TRUE(even.empty());

  odd.insert(odd.end(), {6, 6, 7, 8});
  const auto adjacent_duplicates = odd.unique();
  const auto removed_even = odd.remove_if([](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(adjacent_duplicates, 2U);
  EXPECT_EQ(removed_even, 4U);
  EXPECT_EQ(odd, (std::list<int>{1, 3, 5, 7}));

  // std::sort 需要随机访问，list 应用成员 sort/merge，它们重排节点而非搬移值。
  // merge 要求两边已按同一顺序排序；unique 只压缩相邻等价项，不是全局去重。
  // C++20 的 unique/remove/remove_if 返回删除数量。
}

TEST(List, ReverseAndSwapAlsoPreserveElementIdentity) {
  std::list<std::string> first{"a", "b", "c"};
  std::list<std::string> second{"x"};
  std::string* b_address = &*std::next(first.begin());

  first.reverse();
  first.swap(second);

  EXPECT_EQ(first, (std::list<std::string>{"x"}));
  EXPECT_EQ(second, (std::list<std::string>{"c", "b", "a"}));
  EXPECT_EQ(b_address, &*std::next(second.begin()));

  // reverse 只改变链接，swap 在 allocator 条件允许时交换整组节点；元素地址不变，
  // 但它所属的容器可能改变。保存容器身份与保存元素身份是两件不同的事。
}

TEST(ForwardList, BeforeBeginMakesHeadInsertionAndErasureUniform) {
  std::forward_list<int> values{3, 4};

  auto last_inserted = values.insert_after(values.before_begin(), {1, 2});
  EXPECT_EQ(*last_inserted, 2);
  EXPECT_EQ(values, (std::forward_list<int>{1, 2, 3, 4}));

  auto following = values.erase_after(values.before_begin());
  EXPECT_EQ(*following, 2);
  EXPECT_EQ(values, (std::forward_list<int>{2, 3, 4}));

  // 单向链表无法从当前节点找到前驱，因此修改接口以“前一个位置”为参数。
  // before_begin() 是不可解引用的哨兵位置，使表头也能统一使用 insert_after/erase_after。
}

TEST(ForwardList, ForwardIterationAndNoSizeAvoidHiddenLinearWork) {
  using Values = std::forward_list<int>;

  static_assert(std::ranges::forward_range<Values>);
  static_assert(!std::ranges::bidirectional_range<Values>);
  static_assert(!HasSizeMember<Values>);

  Values values{1, 2, 3, 4};
  EXPECT_EQ(std::distance(values.begin(), values.end()), 4);

  // forward_list 不保存 size 字段，以最小化每个容器对象的开销；求长度必须线性遍历。
  // 若算法频繁需要 size 或倒序遍历，list/vector/deque 通常更合适。
}

TEST(ForwardList, SpliceAfterTransfersNodesAndKeepsTheirAddresses) {
  std::forward_list<std::string> target{"done"};
  std::forward_list<std::string> source{"build", "test"};
  std::string* build_address = &source.front();

  target.splice_after(target.before_begin(), source);

  EXPECT_TRUE(source.empty());
  EXPECT_EQ(
      target,
      (std::forward_list<std::string>{"build", "test", "done"}));
  EXPECT_EQ(build_address, &target.front());

  // splice_after 的位置表示“插到此节点之后”；整表 overload 重连所有 source 节点。
  // 与 list::splice 一样，allocator 必须兼容，节点地址和指向节点的 handle 保持有效。
}

TEST(ForwardList, MemberAlgorithmsWorkWithoutBackPointersOrRandomAccess) {
  std::forward_list<int> first{5, 3, 1, 3};
  std::forward_list<int> second{6, 4, 2};

  first.sort();
  second.sort();
  first.merge(second);
  EXPECT_TRUE(second.empty());

  const auto duplicates = first.unique();
  const auto removed = first.remove_if([](int value) {
    return value > 4;
  });
  first.reverse();

  EXPECT_EQ(duplicates, 1U);
  EXPECT_EQ(removed, 2U);
  EXPECT_EQ(first, (std::forward_list<int>{4, 3, 2, 1}));

  // sort/merge/unique/remove/reverse 都是能直接操作链结的成员函数。merge 前仍需排序；
  // 操作不会凭空变成随机访问，但通常无需移动或复制元素值。
}

}  // namespace
