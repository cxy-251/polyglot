// polyglot-covers:
// - cpp.stdlib.memory.allocator-and-allocator-traits
// - cpp.stdlib.memory.construct-at-and-destroy-at
// - cpp.stdlib.memory.uninitialized-default-and-value-construct
// - cpp.stdlib.memory.uninitialized-fill-copy-and-move
// - cpp.stdlib.memory.uninitialized-algorithm-exception-cleanup
// - cpp.stdlib.memory.destroy-and-destroy-n
// - cpp.stdlib.memory.raw-storage-lifetime-workflow

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <memory>
#include <new>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

struct LifecycleValue {
  static inline int live_count = 0;
  static inline int destructions = 0;

  explicit LifecycleValue(int value = 0) : value(value) { ++live_count; }

  LifecycleValue(const LifecycleValue& other) : value(other.value) {
    ++live_count;
  }

  LifecycleValue(LifecycleValue&& other) noexcept : value(other.value) {
    ++live_count;
    other.value = -1;
  }

  ~LifecycleValue() {
    --live_count;
    ++destructions;
  }

  int value;
};

struct ThrowOnThirdCopy {
  static inline int live_count = 0;
  static inline int copy_attempts = 0;

  explicit ThrowOnThirdCopy(int value) : value(value) { ++live_count; }

  ThrowOnThirdCopy(const ThrowOnThirdCopy& other) : value(other.value) {
    ++copy_attempts;
    if (copy_attempts == 3) {
      throw std::runtime_error{"third copy failed"};
    }
    ++live_count;
  }

  ~ThrowOnThirdCopy() { --live_count; }

  int value;
};

TEST(Allocator, AllocationAndConstructionAreSeparateOperations) {
  using Allocator = std::allocator<LifecycleValue>;
  using Traits = std::allocator_traits<Allocator>;

  LifecycleValue::live_count = 0;
  LifecycleValue::destructions = 0;
  Allocator allocator;
  LifecycleValue* storage = Traits::allocate(allocator, 2);

  EXPECT_EQ(LifecycleValue::live_count, 0);

  Traits::construct(allocator, storage, 7);
  Traits::construct(allocator, storage + 1, 9);
  EXPECT_EQ(LifecycleValue::live_count, 2);
  EXPECT_EQ(storage[0].value + storage[1].value, 16);

  Traits::destroy(allocator, storage + 1);
  Traits::destroy(allocator, storage);
  Traits::deallocate(allocator, storage, 2);

  EXPECT_EQ(LifecycleValue::live_count, 0);
  EXPECT_EQ(LifecycleValue::destructions, 2);

  // allocate 只取得足够且对齐的原始存储，不开始 T 的生命周期；construct/destroy 负责
  // 对象，deallocate 最后归还同样数量的存储。顺序混乱会造成未构造访问或活对象被释放。
}

TEST(ConstructAt, StartsAndEndsAnObjectLifetimeAtAChosenAddress) {
  LifecycleValue::live_count = 0;
  LifecycleValue::destructions = 0;
  alignas(LifecycleValue) std::byte storage[sizeof(LifecycleValue)];

  auto* object = std::construct_at(
      reinterpret_cast<LifecycleValue*>(storage),
      23);
  EXPECT_EQ(object->value, 23);
  EXPECT_EQ(LifecycleValue::live_count, 1);

  std::destroy_at(object);
  EXPECT_EQ(LifecycleValue::live_count, 0);
  EXPECT_EQ(LifecycleValue::destructions, 1);

  // construct_at 是 placement new 的标准包装，destroy_at 对应显式析构。二者不分配或释放
  // 字节；调用方仍负责存储来源、alignment，以及异常路径中每个已构造对象只销毁一次。
}

TEST(UninitializedConstruction, DefaultAndValueFormsDifferForScalarObjects) {
  std::allocator<int> allocator;
  int* storage = allocator.allocate(3);

  int* default_end = std::uninitialized_default_construct_n(storage, 3);
  EXPECT_EQ(default_end, storage + 3);
  storage[0] = 2;
  storage[1] = 3;
  storage[2] = 5;
  EXPECT_EQ(storage[0] + storage[1] + storage[2], 10);
  std::destroy_n(storage, 3);
  allocator.deallocate(storage, 3);

  storage = allocator.allocate(3);
  int* end = std::uninitialized_value_construct_n(storage, 3);
  EXPECT_EQ(end, storage + 3);
  EXPECT_EQ(storage[0], 0);
  EXPECT_EQ(storage[1], 0);
  EXPECT_EQ(storage[2], 0);

  std::destroy_n(storage, 3);
  allocator.deallocate(storage, 3);

  // value_construct 对标量执行零初始化；default_construct 对标量开始生命周期但值不确定，
  // 在赋值前读取会是未定义行为。对类类型，两者都会按各自初始化规则调用构造函数。
}

TEST(UninitializedFill, ConstructsIndependentObjectsAcrossRawStorage) {
  LifecycleValue::live_count = 0;
  LifecycleValue::destructions = 0;
  std::allocator<LifecycleValue> allocator;
  LifecycleValue* storage = allocator.allocate(3);

  {
    LifecycleValue prototype{6};
    std::uninitialized_fill_n(storage, 3, prototype);
    EXPECT_EQ(LifecycleValue::live_count, 4);
  }

  EXPECT_EQ(LifecycleValue::live_count, 3);
  EXPECT_EQ(storage[0].value + storage[1].value + storage[2].value, 18);

  std::destroy(storage, storage + 3);
  allocator.deallocate(storage, 3);
  EXPECT_EQ(LifecycleValue::live_count, 0);

  // uninitialized_fill 在每个目的位置复制构造新对象，不是把一个对象的字节复制多次。
  // 目的区必须是未初始化存储；对已有活对象应使用 fill 赋值而非 uninitialized_fill。
}

TEST(UninitializedCopy, DestroysTheConstructedPrefixWhenACopyThrows) {
  ThrowOnThirdCopy::live_count = 0;
  ThrowOnThirdCopy::copy_attempts = 0;
  std::vector<ThrowOnThirdCopy> source;
  source.reserve(4);
  for (int value = 1; value <= 4; ++value) {
    source.emplace_back(value);
  }
  ASSERT_EQ(ThrowOnThirdCopy::live_count, 4);

  std::allocator<ThrowOnThirdCopy> allocator;
  ThrowOnThirdCopy* storage = allocator.allocate(source.size());
  bool threw = false;

  try {
    ThrowOnThirdCopy* end =
        std::uninitialized_copy(source.begin(), source.end(), storage);
    std::destroy(storage, end);
  } catch (const std::runtime_error&) {
    threw = true;
  }

  EXPECT_TRUE(threw);
  EXPECT_EQ(ThrowOnThirdCopy::copy_attempts, 3);
  EXPECT_EQ(ThrowOnThirdCopy::live_count, 4);
  allocator.deallocate(storage, source.size());

  // 第三个复制构造抛出后，算法自动销毁目的区已成功构造的前缀；源对象不受影响。调用方
  // 仍负责归还原始存储，且不能再次销毁已经由算法回滚的前缀。
}

TEST(UninitializedMove, MovesIntoRawStorageWithoutOwningTheSourceRange) {
  std::vector<std::string> source{"first", "second"};
  std::allocator<std::string> allocator;
  std::string* storage = allocator.allocate(source.size());

  std::string* end =
      std::uninitialized_move(source.begin(), source.end(), storage);
  EXPECT_EQ(storage[0], "first");
  EXPECT_EQ(storage[1], "second");

  std::destroy(storage, end);
  allocator.deallocate(storage, source.size());

  EXPECT_EQ(source.size(), 2U);

  // move 算法不销毁源范围；每个源元素仍有效但值未指定，因此只检查容器结构，不断言字符
  // 串一定为空。目的对象需要调用方销毁，原始 storage 还要按原数量 deallocate。
}

}  // namespace
