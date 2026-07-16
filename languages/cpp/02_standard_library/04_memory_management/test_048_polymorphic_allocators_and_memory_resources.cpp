// polyglot-covers:
// - cpp.stdlib.memory.memory-resource-interface
// - cpp.stdlib.memory.polymorphic-allocator
// - cpp.stdlib.memory.pmr-container-aliases
// - cpp.stdlib.memory.uses-allocator-propagation-in-pmr-containers
// - cpp.stdlib.memory.monotonic-buffer-resource
// - cpp.stdlib.memory.pool-resources
// - cpp.stdlib.memory.null-and-new-delete-resources
// - cpp.stdlib.memory.default-memory-resource

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <memory>
#include <memory_resource>
#include <new>
#include <string>
#include <vector>

namespace {

class CountingResource final : public std::pmr::memory_resource {
 public:
  explicit CountingResource(
      std::pmr::memory_resource* upstream = std::pmr::new_delete_resource())
      : upstream_(upstream) {}

  std::size_t allocation_calls = 0;
  std::size_t deallocation_calls = 0;
  std::size_t allocated_bytes = 0;
  std::size_t deallocated_bytes = 0;

 private:
  void* do_allocate(std::size_t bytes, std::size_t alignment) override {
    ++allocation_calls;
    allocated_bytes += bytes;
    return upstream_->allocate(bytes, alignment);
  }

  void do_deallocate(
      void* pointer,
      std::size_t bytes,
      std::size_t alignment) override {
    ++deallocation_calls;
    deallocated_bytes += bytes;
    upstream_->deallocate(pointer, bytes, alignment);
  }

  bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
    return this == &other;
  }

  std::pmr::memory_resource* upstream_;
};

class DefaultResourceGuard {
 public:
  explicit DefaultResourceGuard(std::pmr::memory_resource* replacement)
      : previous_(std::pmr::set_default_resource(replacement)) {}

  ~DefaultResourceGuard() { std::pmr::set_default_resource(previous_); }

  DefaultResourceGuard(const DefaultResourceGuard&) = delete;
  DefaultResourceGuard& operator=(const DefaultResourceGuard&) = delete;

 private:
  std::pmr::memory_resource* previous_;
};

TEST(MemoryResource, RuntimePolymorphismSeparatesContainersFromAllocationPolicy) {
  CountingResource resource;

  {
    std::pmr::vector<int> values{&resource};
    for (int value = 0; value < 20; ++value) {
      values.push_back(value * value);
    }

    EXPECT_EQ(values[5], 25);
    EXPECT_EQ(values.get_allocator().resource(), &resource);
    EXPECT_GT(resource.allocation_calls, 0U);
  }

  EXPECT_EQ(resource.allocation_calls, resource.deallocation_calls);
  EXPECT_EQ(resource.allocated_bytes, resource.deallocated_bytes);

  // pmr 容器的静态类型不包含具体资源类型，polymorphic_allocator 在运行期转发到
  // memory_resource。资源必须比所有使用它的容器长寿，否则容器析构会调用悬空资源。
}

TEST(PolymorphicAllocator, ManualObjectLifecycleStillUsesTheSelectedResource) {
  CountingResource resource;
  std::pmr::polymorphic_allocator<std::string> allocator{&resource};

  std::string* storage = allocator.allocate(2);
  std::construct_at(storage, "first");
  std::construct_at(storage + 1, "second");

  EXPECT_EQ(storage[0] + " " + storage[1], "first second");
  EXPECT_EQ(allocator.resource(), &resource);

  std::destroy_n(storage, 2);
  allocator.deallocate(storage, 2);
  EXPECT_EQ(resource.allocation_calls, 1U);
  EXPECT_EQ(resource.deallocation_calls, 1U);

  // polymorphic_allocator 仍遵守 allocator 的“存储与对象生命周期分离”规则。resource
  // 收到字节数和 alignment，调用方必须用同一 count 归还相同 allocation。
}

TEST(PmrContainers, NestedAllocatorAwareElementsReceiveTheOuterResource) {
  CountingResource resource;
  std::pmr::vector<std::pmr::string> words{&resource};

  words.emplace_back("a deliberately long string that requires dynamic storage");
  words.emplace_back("another deliberately long string for the same resource");

  ASSERT_EQ(words.size(), 2U);
  EXPECT_EQ(words[0].get_allocator().resource(), &resource);
  EXPECT_EQ(words[1].get_allocator().resource(), &resource);

  // pmr::string 满足 uses_allocator，vector 的 polymorphic_allocator 会在 emplace 时把同一
  // resource 继续传入元素。先在默认资源构造 string 再 push 并不等价，可能先做额外分配。
}

TEST(MonotonicResource, IndividualDeallocationIsDeferredUntilRelease) {
  std::array<std::byte, 64> local_buffer{};
  CountingResource upstream;
  std::pmr::monotonic_buffer_resource arena{
      local_buffer.data(),
      local_buffer.size(),
      &upstream,
  };

  {
    std::pmr::vector<int> values{&arena};
    values.resize(1'000, 7);
    EXPECT_EQ(values.front(), 7);
    EXPECT_GT(upstream.allocation_calls, 0U);
  }

  EXPECT_EQ(upstream.deallocation_calls, 0U);
  arena.release();
  EXPECT_GT(upstream.deallocation_calls, 0U);

  // monotonic resource 的 deallocate 是 no-op，适合整批同寿命对象；release 或资源析构才
  // 归还上游块。必须先析构使用其中存储的对象，再 release，不能把“批量释放”当作析构。
}

TEST(PoolResource, KeepsFreedBlocksForLaterSameSizeAllocationsUntilRelease) {
  CountingResource upstream;
  std::pmr::pool_options options;
  options.max_blocks_per_chunk = 8;
  options.largest_required_pool_block = 128;
  std::pmr::unsynchronized_pool_resource pool{options, &upstream};

  {
    std::pmr::vector<std::pmr::string> values{&pool};
    for (int index = 0; index < 20; ++index) {
      values.emplace_back(40, static_cast<char>('a' + index % 26));
    }
    EXPECT_GT(upstream.allocation_calls, 0U);
  }

  const std::size_t before_release = upstream.deallocation_calls;
  pool.release();
  EXPECT_GT(upstream.deallocation_calls, before_release);

  // pool 按块大小分池并缓存释放块，适合反复分配相近小对象；release 归还所有上游 chunk。
  // unsynchronized 版本本身不做线程同步，多线程共享应使用 synchronized_pool_resource。
}

TEST(StandardResources, NullResourceAlwaysFailsAndDefaultResourceIsObservable) {
  auto* null_resource = std::pmr::null_memory_resource();
  EXPECT_THROW(
      (void)null_resource->allocate(16, alignof(std::max_align_t)),
      std::bad_alloc);

  EXPECT_EQ(
      std::pmr::new_delete_resource(),
      std::pmr::new_delete_resource());

  CountingResource temporary_default;
  {
    DefaultResourceGuard restore_default{&temporary_default};
    std::pmr::vector<int> defaults;
    defaults.push_back(7);

    EXPECT_EQ(std::pmr::get_default_resource(), &temporary_default);
    EXPECT_EQ(defaults.get_allocator().resource(), &temporary_default);
    EXPECT_GT(temporary_default.allocation_calls, 0U);
  }

  // null resource 适合禁止上游扩容并把容量越界变成 bad_alloc。默认资源是进程级可变状态；
  // set_default_resource 只影响之后使用默认构造的 allocator，而且必须恢复原值。库代码
  // 应优先显式接收 resource，避免跨组件隐式耦合。
}

TEST(MemoryResource, EqualityMeansCrossDeallocationIsSupported) {
  CountingResource first;
  CountingResource second;

  EXPECT_TRUE(first.is_equal(first));
  EXPECT_FALSE(first.is_equal(second));
  EXPECT_NE(first, second);

  // resource 相等表示两者可互相 deallocate 对方的 allocation。这里按对象身份相等；即使
  // upstream 相同，两个统计/arena 状态也不同，不能为了“配置相同”谎报相等。
}

}  // namespace
