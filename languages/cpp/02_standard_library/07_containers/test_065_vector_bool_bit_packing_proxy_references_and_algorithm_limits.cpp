// polyglot-covers:
// - cpp.stdlib.containers.vector-bool-space-optimized-specialization
// - cpp.stdlib.containers.vector-bool-proxy-reference
// - cpp.stdlib.containers.vector-bool-flip-and-swap
// - cpp.stdlib.containers.vector-bool-random-access-not-contiguous
// - cpp.stdlib.containers.vector-bool-algorithm-interoperability
// - cpp.stdlib.containers.vector-bool-concurrency-and-addressability-traps

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <class Container>
concept HasBoolPointerData = requires(Container& container) {
  { container.data() } -> std::same_as<bool*>;
};

TEST(VectorBool, ElementAccessReturnsAProxyInsteadOfBoolReference) {
  std::vector<bool> flags{false, true, false};

  auto proxy = flags[0];
  static_assert(!std::is_same_v<decltype(proxy), bool>);
  static_assert(!std::is_same_v<decltype(proxy), bool&>);
  static_assert(std::is_convertible_v<decltype(proxy), bool>);

  proxy = true;
  EXPECT_TRUE(flags[0]);

  bool snapshot = flags[1];
  flags[1] = false;
  EXPECT_TRUE(snapshot);
  EXPECT_FALSE(flags[1]);

  // vector<bool> 可以按位压缩，单个 bit 无法作为普通 bool 对象寻址，因此 operator[]
  // 返回可读写代理。auto proxy 会保留代理并继续关联容器，转换成 bool 才得到独立快照。
}

TEST(VectorBool, ProxyLifetimeStillDependsOnTheContainerStorage) {
  std::vector<bool> flags{true, false};
  auto first = flags.front();

  first = false;
  EXPECT_FALSE(flags.front());

  flags.reserve(flags.capacity() + 8);
  EXPECT_FALSE(flags.front());

  // first 在扩容前只是指向某个存储字的代理；reserve 重分配后它和普通 vector
  // 的元素引用一样失效。这里不再读取 first，只验证容器搬移后的值仍正确。
}

TEST(VectorBool, FlipAndProxySwapOperateOnLogicalBits) {
  std::vector<bool> flags{true, false, true, false};

  flags.flip();
  EXPECT_EQ(flags, (std::vector<bool>{false, true, false, true}));

  std::swap(flags[0], flags[1]);
  EXPECT_EQ(flags, (std::vector<bool>{true, false, false, true}));

  auto first = flags[0];
  first.flip();
  EXPECT_FALSE(flags[0]);

  // specialization 额外提供 flip() 批量翻转；reference 代理也提供 flip，并有专门的
  // swap 支持。不要假设代理类型只有赋值和 bool 转换这两个操作。
}

TEST(VectorBool, IteratorsAreRandomAccessButTheRangeIsNotContiguous) {
  using Flags = std::vector<bool>;

  static_assert(std::ranges::random_access_range<Flags>);
  static_assert(!std::ranges::contiguous_range<Flags>);
  static_assert(!HasBoolPointerData<Flags>);
  static_assert(
      !std::contiguous_iterator<typename Flags::iterator>);

  Flags flags{true, false, true};
  EXPECT_TRUE(*(flags.begin() + 2));

  // 它仍支持随机访问，但没有 bool* 指向压缩 bit，也不提供可用的 data()。
  // 因此不能从 vector<bool> 构造 span<bool>，需要连续 bool 存储时应换用其他表示。
}

TEST(VectorBool, StandardAlgorithmsReadAndWriteThroughTheProxyIterator) {
  std::vector<bool> flags(6, false);

  std::fill(flags.begin() + 1, flags.end() - 1, true);
  const auto true_count = std::ranges::count(flags, true);
  std::reverse(flags.begin(), flags.end());

  EXPECT_EQ(true_count, 4);
  EXPECT_EQ(flags, (std::vector<bool>{false, true, true, true, true, false}));

  std::erase(flags, false);
  EXPECT_EQ(flags, (std::vector<bool>{true, true, true, true}));

  // 代理支持传统 fill/reverse 和只读 ranges::count；但 C++20 的代理迭代器不满足
  // ranges 写算法通常要求的 permutable/indirectly_writable。C++23 才用 const 代理赋值
  // 补足部分概念。要求真正 bool&、bool* 或 contiguous_range 的代码也会拒绝它。
}

TEST(VectorBool, DifferentLogicalElementsMayShareOneUnderlyingMemoryWord) {
  std::vector<bool> flags(64, false);
  flags[0] = true;
  flags[1] = true;

  EXPECT_TRUE(flags[0]);
  EXPECT_TRUE(flags[1]);

  // 相邻 bit 可能共享同一个底层机器字。即使两个线程写不同下标，也可能读改写
  // 同一存储位置而产生数据竞争；不能套用普通 vector“不同元素可并发修改”的保证。
  // 本例只在单线程演示语义，不执行真正的数据竞争。
}

}  // namespace
