// polyglot-covers:
// - cpp.stdlib.concurrency.atomic-generic-type-requirements-default-and-value-initialization
// - cpp.stdlib.concurrency.atomic-load-store-exchange-and-conversion
// - cpp.stdlib.concurrency.atomic-compare-exchange-expected-update-and-spurious-failure
// - cpp.stdlib.concurrency.atomic-integral-fetch-arithmetic-bitwise-and-operators
// - cpp.stdlib.concurrency.atomic-pointer-arithmetic-and-one-past-value
// - cpp.stdlib.concurrency.atomic-floating-fetch-add-and-representation
// - cpp.stdlib.concurrency.atomic-lock-free-properties-and-standard-aliases
// - cpp.stdlib.concurrency.atomic-flag-test-set-clear-and-single-bit-state

#include <gtest/gtest.h>

#include <atomic>
#include <cstdint>
#include <limits>
#include <type_traits>

namespace {

struct TrivialPair {
  int first;
  int second;
};

static_assert(std::is_trivially_copyable_v<TrivialPair>);

TEST(AtomicGeneric, DefaultAndValueConstructionCreateAUsableAtomicObject) {
  std::atomic<int> default_initialized;
  std::atomic<TrivialPair> pair{TrivialPair{1, 2}};

  EXPECT_EQ(default_initialized.load(), 0);
  const auto loaded = pair.load();
  EXPECT_EQ(loaded.first, 1);
  EXPECT_EQ(loaded.second, 2);

  static_assert(!std::is_copy_constructible_v<std::atomic<int>>);
  static_assert(!std::is_copy_assignable_v<std::atomic<int>>);

  // C++20 的 atomic 默认构造会以 T() 初始化值；早期标准的默认构造不保证已初始化。
  // T 必须满足 trivially copyable 等约束，atomic 自身不可复制，值要通过 load 取出。
}

TEST(AtomicCoreOperations, LoadStoreConversionAndExchangeHaveDistinctRoles) {
  std::atomic<int> value{3};
  EXPECT_EQ(value.load(std::memory_order_relaxed), 3);

  value.store(4, std::memory_order_release);
  const int converted = value;
  EXPECT_EQ(converted, 4);

  const int old = value.exchange(9, std::memory_order_acq_rel);
  EXPECT_EQ(old, 4);
  EXPECT_EQ(value.load(), 9);

  // 隐式转换等价于 seq_cst load；赋值运算等价于 store 且返回写入值。exchange 是
  // 单个不可分割的 read-modify-write，返回旧值，不等价于分离的 load+store。
}

TEST(AtomicCompareExchange, FailureOverwritesExpectedWithTheObservedValue) {
  std::atomic<int> value{5};
  int expected = 3;

  EXPECT_FALSE(value.compare_exchange_strong(expected, 7));
  EXPECT_EQ(expected, 5);
  EXPECT_EQ(value.load(), 5);

  EXPECT_TRUE(value.compare_exchange_strong(expected, 7));
  EXPECT_EQ(expected, 5);
  EXPECT_EQ(value.load(), 7);

  // CAS 成功时把 expected 对应值替换为 desired；失败时不写原子对象，却把实际值
  // 写回 expected。这使典型重试循环无需额外 load，也容易误伤仍需旧期望值的代码。
}

TEST(AtomicCompareExchange, WeakFormBelongsInARetryLoop) {
  std::atomic<int> value{10};
  int expected = value.load(std::memory_order_relaxed);

  while (!value.compare_exchange_weak(
      expected, expected + 1, std::memory_order_relaxed,
      std::memory_order_relaxed)) {
    // weak CAS 即使表示相等也允许伪失败；失败后 expected 已刷新，重新计算 desired。
  }
  EXPECT_EQ(value.load(std::memory_order_relaxed), 11);

  // strong 更适合不循环的一次判断；weak 常能映射到更轻量硬件指令。failure order
  // 不能是 release/acq_rel，也不能强于 success order，这些是调用前置条件。
}

TEST(AtomicIntegral, FetchOperationsReturnOldValueAndOperatorsReturnNewValue) {
  std::atomic<unsigned> bits{0b0011U};

  EXPECT_EQ(bits.fetch_or(0b0100U), 0b0011U);
  EXPECT_EQ(bits.load(), 0b0111U);
  EXPECT_EQ(bits.fetch_and(0b0110U), 0b0111U);
  EXPECT_EQ(bits.fetch_xor(0b0011U), 0b0110U);
  EXPECT_EQ(bits.load(), 0b0101U);

  std::atomic<int> count{4};
  EXPECT_EQ(count.fetch_add(3), 4);
  EXPECT_EQ(count.fetch_sub(2), 7);
  EXPECT_EQ(++count, 6);
  EXPECT_EQ(count++, 6);
  EXPECT_EQ(count.load(), 7);

  // fetch_* 返回修改前的值；复合赋值和前置 ++ 返回新值，后置 ++ 返回旧值。
  // 有符号原子整数算术使用二进制补码，不会因普通整数溢出规则产生未定义行为。
}

TEST(AtomicPointer, FetchArithmeticScalesByThePointedToType) {
  int values[] = {10, 20, 30};
  std::atomic<int*> cursor{values};

  int* old = cursor.fetch_add(2);
  EXPECT_EQ(old, &values[0]);
  EXPECT_EQ(cursor.load(), &values[2]);
  EXPECT_EQ(*(cursor -= 1), 20);

  int* one_past = cursor.fetch_add(2) + 2;
  EXPECT_EQ(one_past, values + 3);
  EXPECT_EQ(cursor.load(), values + 3);

  // 指针 fetch_add/sub 按元素而非字节移动，可得到 one-past 指针，但不能解引用它。
  // 标准还允许结果地址不可访问；原子性只保护指针值，不延长 pointee 生命周期。
}

TEST(AtomicFloating, FetchAddProvidesAnAtomicFloatingReadModifyWrite) {
  std::atomic<double> value{1.5};

  EXPECT_DOUBLE_EQ(value.fetch_add(0.25), 1.5);
  EXPECT_DOUBLE_EQ(value.load(), 1.75);
  EXPECT_DOUBLE_EQ(value.fetch_sub(0.5), 1.75);
  EXPECT_DOUBLE_EQ(value.load(), 1.25);

  // C++20 为浮点 atomic 增加 fetch_add/sub。运算不要求遵守调用线程当前浮点环境；
  // 若结果无法表示也不产生未定义行为，但结果值由实现的浮点表示决定。
}

TEST(AtomicProperties, LockFreeQueriesDescribeImplementationNotOrderingStrength) {
  std::atomic<int> value{0};
  const bool runtime_lock_free = value.is_lock_free();
  EXPECT_EQ(runtime_lock_free, std::atomic<int>::is_always_lock_free);

  static_assert(std::is_same_v<std::atomic_int, std::atomic<int>>);
  static_assert(std::is_same_v<std::atomic_uint64_t, std::atomic<std::uint64_t>>);
  static_assert(ATOMIC_BOOL_LOCK_FREE >= 0 && ATOMIC_BOOL_LOCK_FREE <= 2);
  static_assert(ATOMIC_INT_LOCK_FREE >= 0 && ATOMIC_INT_LOCK_FREE <= 2);

  // is_lock_free 只说明该对象的操作是否用无锁实现；0/1/2 宏分别表示从不/有时/总是。
  // lock-free 不等于 wait-free，也不改变 memory_order，且不同类型结果可以不同。
}

TEST(AtomicFlag, TestAndSetReturnsTheOldBitAndClearResetsIt) {
  std::atomic_flag flag{};
  EXPECT_FALSE(flag.test(std::memory_order_relaxed));
  EXPECT_FALSE(flag.test_and_set(std::memory_order_acquire));
  EXPECT_TRUE(flag.test_and_set(std::memory_order_relaxed));
  EXPECT_TRUE(flag.test(std::memory_order_relaxed));
  flag.clear(std::memory_order_release);
  EXPECT_FALSE(flag.test(std::memory_order_relaxed));

  // atomic_flag 保证 lock-free，只表达一个 bit。test 是 C++20 新增的纯读取；
  // test_and_set 是 RMW。自旋锁还需正确内存序和退避，通常不如标准 mutex 合适。
}

}  // namespace
