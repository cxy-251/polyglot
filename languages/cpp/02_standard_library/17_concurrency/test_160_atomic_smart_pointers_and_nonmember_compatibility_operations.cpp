// polyglot-covers:
// - cpp.stdlib.concurrency.atomic-shared-ptr-load-store-exchange-and-use-count
// - cpp.stdlib.concurrency.atomic-shared-ptr-compare-exchange-equivalence
// - cpp.stdlib.concurrency.atomic-shared-ptr-wait-notify-and-lifetime
// - cpp.stdlib.concurrency.atomic-weak-ptr-load-exchange-lock-and-expiration
// - cpp.stdlib.concurrency.atomic-smart-pointer-lock-free-query-and-feature-detection
// - cpp.stdlib.concurrency.shared-ptr-atomic-free-functions-legacy-compatibility
// - cpp.stdlib.concurrency.atomic-nonmember-load-store-exchange-compare-and-fetch
// - cpp.stdlib.concurrency.atomic-flag-nonmember-and-wait-notify-functions
// - cpp.stdlib.concurrency.atomic-wait-notify-nonmember-functions
// - cpp.stdlib.concurrency.atomic-init-and-cxx20-initialization-transition

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <future>
#include <memory>
#include <thread>
#include <type_traits>

namespace {

#if defined(__cpp_lib_atomic_shared_ptr)

TEST(AtomicSharedPtr, LoadStoreAndExchangeManageOwnershipAtomically) {
  auto first = std::make_shared<int>(1);
  auto second = std::make_shared<int>(2);
  std::atomic<std::shared_ptr<int>> owner{first};

  auto loaded = owner.load(std::memory_order_acquire);
  EXPECT_EQ(loaded, first);
  EXPECT_GE(first.use_count(), 3);  // first、owner 内部值、loaded。

  auto old = owner.exchange(second, std::memory_order_acq_rel);
  EXPECT_EQ(old, first);
  EXPECT_EQ(owner.load(), second);
  owner.store(nullptr);
  EXPECT_EQ(owner.load(), nullptr);

  // shared_ptr 控制块的 use_count 增量属于原子操作；相应减量和对象删除排在更新之后，
  // 但通常不是原子更新本身的一部分。已 load 的副本继续独立延长旧对象寿命。
}

TEST(AtomicSharedPtr, CompareExchangeUpdatesExpectedAndComparesSharedOwnership) {
  auto first = std::make_shared<int>(1);
  auto second = std::make_shared<int>(2);
  auto replacement = std::make_shared<int>(3);
  std::atomic<std::shared_ptr<int>> owner{second};

  auto expected = first;
  EXPECT_FALSE(owner.compare_exchange_strong(expected, replacement));
  EXPECT_EQ(expected, second);

  EXPECT_TRUE(owner.compare_exchange_strong(expected, replacement));
  EXPECT_EQ(owner.load(), replacement);

  // atomic<shared_ptr> 的 CAS 像普通 atomic 一样在失败时覆盖 expected；比较要求指针
  // 值相同且共享同一所有权（或两者皆空），不能只凭 get() 地址推断控制块相同。
}

TEST(AtomicSharedPtr, WaitObservesPointerChangeAndLoadedCopyKeepsOldObjectAlive) {
  auto first = std::make_shared<int>(7);
  auto second = std::make_shared<int>(8);
  std::atomic<std::shared_ptr<int>> owner{first};
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<std::shared_ptr<int>> observed;
  auto observed_future = observed.get_future();

  std::thread waiter{[&] {
    auto old = owner.load();
    entered.set_value();
    owner.wait(old);
    observed.set_value(owner.load());
    EXPECT_EQ(*old, 7);
  }};
  entered_future.wait();
  owner.store(second);
  owner.notify_one();

  EXPECT_EQ(observed_future.get(), second);
  waiter.join();

  // wait 比较 atomic 中的 shared_ptr 值；waiter 的 old 副本保证旧 pointee 在等待期间
  // 存活。notify 仍必须配合值变化，所有权管理并不会把通知变成事件队列。
}

TEST(AtomicWeakPtr, AtomicHandleDoesNotKeepThePointeeAlive) {
  auto strong = std::make_shared<int>(41);
  std::weak_ptr<int> weak = strong;
  std::atomic<std::weak_ptr<int>> observer{weak};

  auto loaded = observer.load();
  ASSERT_FALSE(loaded.expired());
  EXPECT_EQ(*loaded.lock(), 41);

  const auto old = observer.exchange(std::weak_ptr<int>{});
  EXPECT_FALSE(old.expired());
  strong.reset();
  EXPECT_TRUE(old.expired());
  EXPECT_TRUE(observer.load().expired());

  // atomic<weak_ptr> 原子地更新观察句柄，却不会增加 shared owner 数量；load 得到的
  // weak_ptr 仍须 lock，并检查结果是否为空，不能先 expired 再假设 lock 必成功。
}

TEST(AtomicSmartPointerProperties, FeatureAndLockFreeQueriesAreExplicit) {
  static_assert(__cpp_lib_atomic_shared_ptr >= 201711L);

  std::atomic<std::shared_ptr<int>> shared;
  std::atomic<std::weak_ptr<int>> weak;
  EXPECT_FALSE(shared.is_lock_free());
  EXPECT_FALSE(weak.is_lock_free());

  // C++20 特化让接口与 atomic<T> 一致；是否 lock-free 仍由实现决定。本基线的
  // libstdc++ 11 用内部锁，不能把这里的 false 泛化到其他标准库或平台。
}

#else

TEST(AtomicSmartPointerProperties, MissingLibraryFeatureIsReportedExplicitly) {
  GTEST_SKIP() << "the active standard library lacks C++20 atomic smart pointers";

  // 这是标准库实现能力缺口，不是语言模式缺失；源码仍保留完整案例，换到声明
  // __cpp_lib_atomic_shared_ptr >= 201711L 的标准库后会自动编译并运行上面的分支。
}

#endif

TEST(SharedPtrAtomicFreeFunctions, LegacyInterfaceOperatesOnASharedPtrObject) {
  std::shared_ptr<int> slot;
  auto first = std::make_shared<int>(1);
  auto second = std::make_shared<int>(2);

  std::atomic_store_explicit(&slot, first, std::memory_order_release);
  EXPECT_EQ(std::atomic_load_explicit(&slot, std::memory_order_acquire), first);
  EXPECT_EQ(std::atomic_exchange(&slot, second), first);

  auto expected = second;
  EXPECT_TRUE(std::atomic_compare_exchange_strong(
      &slot, &expected, std::shared_ptr<int>{}));
  EXPECT_EQ(std::atomic_load(&slot), nullptr);

  // 这些只接受 shared_ptr* 的自由函数是 C++11 兼容接口，C++20 已有更统一的
  // atomic<shared_ptr<T>>；同一 slot 的并发访问必须全部走原子接口，不能混用普通赋值。
}

TEST(AtomicFreeFunctions, GenericOperationsMirrorAtomicMemberFunctions) {
  std::atomic<int> value;
  std::atomic_init(&value, 3);
  EXPECT_EQ(std::atomic_load(&value), 3);

  std::atomic_store_explicit(&value, 4, std::memory_order_release);
  EXPECT_EQ(std::atomic_exchange_explicit(
                &value, 5, std::memory_order_acq_rel),
            4);
  int expected = 5;
  EXPECT_TRUE(std::atomic_compare_exchange_weak_explicit(
      &value, &expected, 6, std::memory_order_acq_rel,
      std::memory_order_acquire));
  EXPECT_EQ(std::atomic_fetch_add(&value, 2), 6);
  EXPECT_EQ(std::atomic_fetch_sub_explicit(
                &value, 1, std::memory_order_relaxed),
            8);
  EXPECT_EQ(value.load(), 7);

  // 非成员模板与成员操作语义相同，主要服务泛型/旧代码。atomic_init 在 C++20 默认
  // 构造已经初始化值后失去必要性；它只能用于尚未被其他线程访问的 atomic 对象。
}

TEST(AtomicFreeFunctions, IntegralBitwiseAndPointerFetchOperationsAreAvailable) {
  std::atomic<unsigned> bits{0b0011U};
  EXPECT_EQ(std::atomic_fetch_or(&bits, 0b0100U), 0b0011U);
  EXPECT_EQ(std::atomic_fetch_and(&bits, 0b0110U), 0b0111U);
  EXPECT_EQ(std::atomic_fetch_xor(&bits, 0b0011U), 0b0110U);
  EXPECT_EQ(bits.load(), 0b0101U);

  int values[] = {1, 2, 3};
  std::atomic<int*> cursor{values};
  EXPECT_EQ(std::atomic_fetch_add(&cursor, 2), values);
  EXPECT_EQ(std::atomic_fetch_sub(&cursor, 1), values + 2);
  EXPECT_EQ(cursor.load(), values + 1);
}

TEST(AtomicFreeFunctions, WaitAndNotifyFormsOperateOnTheSameAtomicObject) {
  std::atomic<int> value{1};
  std::atomic_wait_explicit(&value, 0, std::memory_order_relaxed);
  EXPECT_EQ(std::atomic_load(&value), 1);
  std::atomic_notify_one(&value);
  std::atomic_notify_all(&value);

  // 当前值已不同于 old 时 atomic_wait 直接返回；自由函数只是成员 wait/notify 的
  // 泛型兼容入口，不保存通知，也不允许传入普通 T*。
}

TEST(AtomicFlagFreeFunctions, LegacyAndCxx20WaitingFormsShareOneFlag) {
  std::atomic_flag flag{};
  EXPECT_FALSE(std::atomic_flag_test(&flag));
  EXPECT_FALSE(std::atomic_flag_test_and_set_explicit(
      &flag, std::memory_order_acquire));
  EXPECT_TRUE(std::atomic_flag_test_explicit(
      &flag, std::memory_order_relaxed));
  std::atomic_flag_clear_explicit(&flag, std::memory_order_release);
  EXPECT_FALSE(std::atomic_flag_test(&flag));

  std::atomic_flag_wait_explicit(
      &flag, true, std::memory_order_relaxed);  // 当前 false，不会阻塞。
  std::atomic_flag_notify_all(&flag);

  // C++20 为自由函数族同样加入 test/wait/notify；它们操作传入对象，并不建立另一份
  // 状态。ATOMIC_FLAG_INIT/ATOMIC_VAR_INIT 属于旧初始化风格，新代码优先花括号初始化。
}

}  // namespace
