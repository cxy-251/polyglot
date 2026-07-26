// polyglot-covers:
// - cpp.stdlib.containers.vector-construction-assignment-and-bounds
// - cpp.stdlib.containers.vector-contiguous-storage-and-data
// - cpp.stdlib.containers.vector-size-capacity-reserve-and-shrink
// - cpp.stdlib.containers.vector-push-emplace-and-insert-return-values
// - cpp.stdlib.containers.vector-resize-value-initialization
// - cpp.stdlib.containers.vector-insertion-and-erasure-invalidation
// - cpp.stdlib.containers.vector-erase-and-erase-if
// - cpp.stdlib.containers.vector-move-only-elements

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <memory>
#include <ranges>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

TEST(Vector, ConstructionAssignmentAndCheckedAccessHaveDifferentRoles) {
  std::vector<int> counted(3, 7);
  std::vector<int> listed{3, 7};
  std::vector<int> copied(listed.begin(), listed.end());

  EXPECT_EQ(counted, (std::vector<int>{7, 7, 7}));
  EXPECT_EQ(listed, (std::vector<int>{3, 7}));
  EXPECT_EQ(copied, listed);

  counted.assign({2, 3, 5, 7});
  EXPECT_EQ(counted.front(), 2);
  EXPECT_EQ(counted.back(), 7);
  EXPECT_THROW((void)counted.at(4), std::out_of_range);

  // `(count, value)` 与 initializer_list 很容易视觉混淆：圆括号生成三个 7，
  // 花括号生成两个元素。at() 检查边界；operator[]、front()、back() 依赖调用者
  // 满足索引有效或容器非空的前置条件。
}

TEST(Vector, DataAndIteratorsExposeContiguousStorage) {
  std::vector<int> values{2, 3, 5, 7};

  static_assert(std::ranges::contiguous_range<decltype(values)>);
  static_assert(std::same_as<decltype(values)::value_type, int>);
  EXPECT_EQ(values.data(), &values[0]);
  EXPECT_EQ(values.data() + values.size(), std::to_address(values.end()));

  std::span<int> view{values};
  view[1] = 30;
  EXPECT_EQ(values[1], 30);

  std::vector<int> empty;
  EXPECT_EQ(empty.begin(), empty.end());

  // 非空 vector 的元素连续，因此可直接构造 span 或交给需要指针和长度的接口。
  // 空 vector 的 data() 可以是空指针，也可以是某个不可解引用值，代码不应断言其表示。
}

TEST(Vector, ReserveChangesCapacityWithoutCreatingElements) {
  std::vector<int> values{1, 2, 3};
  const auto original_size = values.size();
  const auto requested = values.capacity() + 20;
  const int* old_data = values.data();

  values.reserve(requested);

  EXPECT_EQ(values.size(), original_size);
  EXPECT_GE(values.capacity(), requested);
  EXPECT_NE(values.data(), old_data);

  const auto grown_capacity = values.capacity();
  values.reserve(1);
  EXPECT_EQ(values.capacity(), grown_capacity);

  values.shrink_to_fit();
  EXPECT_GE(values.capacity(), values.size());

  // reserve(new_cap) 只预留存储，不构造元素；new_cap 大于旧 capacity 时保证重分配。
  // 较小的 reserve 不会缩容，shrink_to_fit 也只是非强制请求，不能断言 capacity==size。
}

TEST(Vector, EmplaceAndInsertReturnHandlesToTheInsertedElements) {
  struct Record {
    std::string name;
    int score;
  };

  std::vector<Record> records;
  records.reserve(4);

  Record& first = records.emplace_back(Record{"Ada", 10});
  EXPECT_EQ(&first, &records.back());

  auto inserted = records.emplace(records.begin(), Record{"Bjarne", 20});
  EXPECT_EQ(inserted->name, "Bjarne");

  const std::array<Record, 2> more{{{"Grace", 30}, {"Dennis", 40}}};
  auto range_first = records.insert(records.end(), more.begin(), more.end());
  EXPECT_EQ(range_first->name, "Grace");
  EXPECT_EQ(records.back().name, "Dennis");

  // emplace 在目标位置直接构造元素，但扩容或中间搬移仍可能发生；它不是“永不移动”。
  // emplace_back 返回新元素引用，insert/emplace(position, ...) 返回新元素迭代器。
}

TEST(Vector, ResizeChangesSizeAndValueInitializesNewElements) {
  std::vector<int> values{1, 2, 3};

  values.resize(5);
  EXPECT_EQ(values, (std::vector<int>{1, 2, 3, 0, 0}));

  values.resize(7, 9);
  EXPECT_EQ(values, (std::vector<int>{1, 2, 3, 0, 0, 9, 9}));

  values.resize(2);
  EXPECT_EQ(values, (std::vector<int>{1, 2}));

  // resize 增长时，未给 value 的新 int 会值初始化为 0；给定 value 时复制该值。
  // 缩小时销毁尾部元素但不承诺归还 capacity，reserve 则完全不改变 size。
}

TEST(Vector, ReallocationInvalidatesEveryHandleToElements) {
  std::vector<int> values{10, 20, 30};
  const auto requested = values.capacity() + 1;
  const int* old_data = values.data();

  values.reserve(requested);
  const int* new_data = values.data();

  EXPECT_NE(new_data, old_data);
  EXPECT_EQ(values, (std::vector<int>{10, 20, 30}));

  // 一旦重分配，所有旧 iterator、pointer、reference 都悬空；这里只比较保存的地址值，
  // 不解引用旧指针。不要把 vector 元素引用跨越可能扩容的 push/insert/reserve 保存。
}

TEST(Vector, InsertionWithoutReallocationStillInvalidatesAtAndAfterThePosition) {
  std::vector<int> values{1, 3, 4};
  values.reserve(8);
  int* first_address = &values[0];
  const auto old_capacity = values.capacity();

  auto inserted = values.insert(values.begin() + 1, 2);

  EXPECT_EQ(values.capacity(), old_capacity);
  EXPECT_EQ(&values[0], first_address);
  EXPECT_EQ(inserted, values.begin() + 1);
  EXPECT_EQ(values, (std::vector<int>{1, 2, 3, 4}));

  // 没有重分配时，插入点之前的 handle 保持有效；插入点及之后的元素因搬移而失效。
  // 原 end() 也失效。预留容量只能避免“全部失效”，不能让中间插入稳定。
}

TEST(Vector, EraseReturnsTheFollowingElementAndInvalidatesTheSuffix) {
  std::vector<int> values{2, 3, 5, 7, 11};
  int* first_address = &values.front();

  auto following = values.erase(values.begin() + 1, values.begin() + 3);

  EXPECT_EQ(values, (std::vector<int>{2, 7, 11}));
  EXPECT_EQ(following, values.begin() + 1);
  EXPECT_EQ(*following, 7);
  EXPECT_EQ(&values.front(), first_address);

  // erase 返回被删区间之后的新位置，适合在循环中接着遍历。删除点之前的 handle
  // 保持有效，删除点及之后（包括旧 end）失效；capacity 通常不会因此下降。
}

TEST(Vector, FreeEraseFunctionsExpressTheEraseRemoveWorkflow) {
  std::vector<int> values{1, 2, 3, 2, 4, 2};

  const auto twos = std::erase(values, 2);
  const auto evens = std::erase_if(values, [](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(twos, 3U);
  EXPECT_EQ(evens, 1U);
  EXPECT_EQ(values, (std::vector<int>{1, 3}));

  // C++20 的 std::erase/std::erase_if 封装 erase-remove 惯用法并返回删除数量。
  // 单独调用 std::remove 只把保留元素搬到前方，不会改变容器 size。
}

TEST(Vector, MoveOnlyElementsWorkWithMoveInsertionAndOwnershipTransfer) {
  std::vector<std::unique_ptr<int>> owners;
  auto first = std::make_unique<int>(7);

  owners.push_back(std::move(first));
  owners.emplace_back(std::make_unique<int>(11));

  EXPECT_EQ(first, nullptr);
  ASSERT_EQ(owners.size(), 2U);
  EXPECT_EQ(*owners[0], 7);
  EXPECT_EQ(*owners[1], 11);

  auto released = std::move(owners.back());
  owners.pop_back();
  EXPECT_EQ(*released, 11);
  EXPECT_EQ(owners.size(), 1U);

  // vector 只要求实际操作所需的元素能力；移动专属类型可以存储，但复制整个 vector
  // 或调用需要复制元素的 overload 不可行。pop_back 只销毁元素，不返回其值，应先移动出来。
}

}  // namespace
