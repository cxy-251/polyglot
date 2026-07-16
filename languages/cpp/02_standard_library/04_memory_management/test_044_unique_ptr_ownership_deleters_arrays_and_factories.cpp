// polyglot-covers:
// - cpp.stdlib.memory.unique-ptr-exclusive-ownership
// - cpp.stdlib.memory.make-unique
// - cpp.stdlib.memory.unique-ptr-move-reset-release-and-swap
// - cpp.stdlib.memory.unique-ptr-custom-deleter
// - cpp.stdlib.memory.unique-ptr-array-specialization
// - cpp.stdlib.memory.unique-ptr-polymorphic-conversion
// - cpp.stdlib.memory.unique-ptr-factory-exception-safety
// - cpp.stdlib.memory.make-unique-for-overwrite
// - cpp.stdlib.memory.make-and-allocate-shared-for-overwrite
// - cpp.implementation.libstdcxx11-smart-ptr-for-overwrite-gap

#include <gtest/gtest.h>

#include <memory>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct TrackedResource {
  static inline int live_count = 0;

  explicit TrackedResource(int value) : value(value) { ++live_count; }
  ~TrackedResource() { --live_count; }

  int value;
};

struct LoggingDeleter {
  std::vector<std::string>* events;
  std::string label;

  void operator()(TrackedResource* resource) const noexcept {
    events->push_back(label + ":" + std::to_string(resource->value));
    delete resource;
  }
};

struct PolymorphicBase {
  virtual ~PolymorphicBase() = default;
  virtual std::string kind() const { return "base"; }
};

struct PolymorphicDerived : PolymorphicBase {
  std::string kind() const override { return "derived"; }
};

std::unique_ptr<TrackedResource> make_resource_or_throw(bool fail) {
  auto resource = std::make_unique<TrackedResource>(41);
  if (fail) {
    throw std::runtime_error{"factory failed"};
  }
  return resource;
}

TEST(UniquePtr, MoveTransfersExclusiveOwnershipAndEmptiesTheSource) {
  TrackedResource::live_count = 0;
  auto first = std::make_unique<TrackedResource>(7);
  static_assert(!std::is_copy_constructible_v<decltype(first)>);

  auto second = std::move(first);

  EXPECT_EQ(first, nullptr);
  ASSERT_NE(second, nullptr);
  EXPECT_EQ(second->value, 7);
  EXPECT_EQ(TrackedResource::live_count, 1);

  second.reset();
  EXPECT_EQ(TrackedResource::live_count, 0);

  // unique_ptr 不能复制；移动把 pointer 和 deleter 状态交给目标，并把源设为空。空对象仍
  // 可析构、reset 或再次赋值，移动后的源不需要特殊清理。
}

TEST(UniquePtr, ResetReleaseAndSwapHaveDifferentOwnershipEffects) {
  TrackedResource::live_count = 0;
  auto first = std::make_unique<TrackedResource>(1);
  auto second = std::make_unique<TrackedResource>(2);

  first.swap(second);
  EXPECT_EQ(first->value, 2);
  EXPECT_EQ(second->value, 1);

  TrackedResource* released = second.release();
  EXPECT_EQ(second, nullptr);
  EXPECT_EQ(TrackedResource::live_count, 2);

  second.reset(released);
  first.reset(new TrackedResource{3});
  EXPECT_EQ(first->value, 3);
  EXPECT_EQ(TrackedResource::live_count, 2);

  // reset 先用 deleter 释放旧对象再接管新指针；release 只交出裸指针，绝不删除。release
  // 后若没有立刻转交给另一个 owner，就会泄漏；本例马上由 second 重新接管。
}

TEST(UniquePtr, StatefulCustomDeleterTravelsWithOwnership) {
  TrackedResource::live_count = 0;
  std::vector<std::string> events;

  {
    std::unique_ptr<TrackedResource, LoggingDeleter> resource{
        new TrackedResource{9},
        LoggingDeleter{&events, "close"},
    };

    auto moved = std::move(resource);
    EXPECT_EQ(resource, nullptr);
    EXPECT_EQ(moved.get_deleter().label, "close");
  }

  EXPECT_EQ(events, (std::vector<std::string>{"close:9"}));
  EXPECT_EQ(TrackedResource::live_count, 0);

  // deleter 是 unique_ptr 类型和状态的一部分，移动所有权也移动 deleter。deleter 调用不得
  // 抛异常，否则 unique_ptr 析构的 noexcept 边界会导致 terminate。
}

TEST(UniquePtrArrays, ArraySpecializationUsesDeleteArrayAndSubscript) {
  auto values = std::make_unique<int[]>(4);

  EXPECT_EQ(values[0], 0);
  for (int index = 0; index < 4; ++index) {
    values[index] = (index + 1) * 10;
  }
  EXPECT_EQ(values[3], 40);

  // make_unique<T[]>(n) value-initialize 每个元素，并由 unique_ptr<T[]> 自动调用 delete[]。
  // 该 specialization 提供 operator[] 但不保存长度；越界仍是未定义行为，应另存 size。
}

TEST(UniquePtr, DerivedOwnershipConvertsOnlyWhenPointerAndDeleterAreCompatible) {
  std::unique_ptr<PolymorphicDerived> derived =
      std::make_unique<PolymorphicDerived>();
  std::unique_ptr<PolymorphicBase> base = std::move(derived);

  EXPECT_EQ(derived, nullptr);
  EXPECT_EQ(base->kind(), "derived");

  // Derived* 可转换为 Base* 且 default_delete 也可转换时，unique_ptr 支持所有权上转型。
  // 通过 Base 删除仍要求 virtual destructor；否则转换虽然可能编译，最终 delete 却是 UB。
}

TEST(UniquePtrFactories, LocalOwnerCleansUpWhenLaterFactoryWorkThrows) {
  TrackedResource::live_count = 0;

  EXPECT_THROW((void)make_resource_or_throw(true), std::runtime_error);
  EXPECT_EQ(TrackedResource::live_count, 0);

  auto resource = make_resource_or_throw(false);
  ASSERT_NE(resource, nullptr);
  EXPECT_EQ(resource->value, 41);
  EXPECT_EQ(TrackedResource::live_count, 1);

  // make_unique 在单个表达式内完成分配和构造，返回后立刻由局部 owner 管理。工厂后续步骤
  // 抛异常时栈展开自动删除对象，比手写 new 后经过多步才交给 unique_ptr 更稳妥。
}

TEST(UniquePtrFactories, ForOverwriteSkipsValueInitializationForTrivialStorage) {
#ifdef __cpp_lib_smart_ptr_for_overwrite
  auto values = std::make_unique_for_overwrite<int[]>(3);
  values[0] = 2;
  values[1] = 3;
  values[2] = 5;

  EXPECT_EQ(values[0] + values[1] + values[2], 10);

  auto shared_values = std::make_shared_for_overwrite<int[]>(2);
  shared_values[0] = 7;
  shared_values[1] = 11;
  EXPECT_EQ(shared_values[0] + shared_values[1], 18);

  auto allocated_values =
      std::allocate_shared_for_overwrite<int[]>(std::allocator<int>{}, 2);
  allocated_values[0] = 13;
  allocated_values[1] = 17;
  EXPECT_EQ(allocated_values[0] + allocated_values[1], 30);

  // for_overwrite 对 trivial 元素做 default-initialization，初始 int 值不确定，必须先完整
  // 覆写再读取；unique/shared/allocate_shared 版本适合马上由 read/decode 填满的大缓冲区，
  // 不适合作为普通零值工厂。
#else
  // GCC 11.4 的 libstdc++ 未定义 __cpp_lib_smart_ptr_for_overwrite，因此整组 C++20 API
  // 无法在当前基线实例化；保留条件分支，使升级工具链后自动转为真实编译与运行覆盖。
  GTEST_SKIP() << "libstdc++ 11.4 lacks C++20 smart_ptr_for_overwrite";
#endif
}

}  // namespace
