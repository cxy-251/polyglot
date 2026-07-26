// polyglot-covers:
// - cpp.stdlib.concurrency.mutex-mutual-exclusion-and-synchronizes-with-unlock
// - cpp.stdlib.concurrency.mutex-try-lock-failure-and-spurious-permission
// - cpp.stdlib.concurrency.recursive-mutex-reentrant-ownership-depth
// - cpp.stdlib.concurrency.lock-guard-raii-and-adopt-lock
// - cpp.stdlib.concurrency.scoped-lock-multiple-mutex-deadlock-avoidance
// - cpp.stdlib.concurrency.generic-lock-and-adopted-guards
// - cpp.stdlib.concurrency.generic-try-lock-failure-index-and-rollback
// - cpp.stdlib.concurrency.lock-tags-defer-try-adopt-precondition-traps
// - cpp.stdlib.concurrency.mutex-destruction-and-unowned-unlock-traps

#include <gtest/gtest.h>

#include <future>
#include <mutex>
#include <thread>
#include <type_traits>
#include <vector>

namespace {

TEST(MutexSynchronization, LockGuardProtectsACompoundReadModifyWrite) {
  std::mutex mutex;
  int counter = 0;
  std::vector<std::thread> workers;
  for (int worker = 0; worker < 4; ++worker) {
    workers.emplace_back([&] {
      for (int iteration = 0; iteration < 1000; ++iteration) {
        const std::lock_guard<std::mutex> guard{mutex};
        ++counter;
      }
    });
  }
  for (auto& worker : workers) {
    worker.join();
  }

  EXPECT_EQ(counter, 4000);

  // ++counter 是读-改-写复合操作；mutex 的 unlock 与后来成功 lock 建立
  // synchronizes-with，使临界区内的普通内存访问可见，而不只是防止同一时刻进入。
}

TEST(MutexTryLock, FailureIsObservedFromAnotherOwnerWithoutBlocking) {
  std::mutex mutex;
  std::promise<void> locked;
  auto locked_future = locked.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  std::thread owner{[&] {
    const std::lock_guard<std::mutex> guard{mutex};
    locked.set_value();
    release_future.wait();
  }};
  locked_future.wait();

  EXPECT_FALSE(mutex.try_lock());
  release.set_value();
  owner.join();
  ASSERT_TRUE(mutex.try_lock());
  mutex.unlock();

  // try_lock 立即返回，标准还允许在互斥量实际空闲时偶发返回 false，因此失败不能
  // 证明“另一个线程一定持有锁”。成功则获得所有权并建立与此前 unlock 的同步。
}

TEST(RecursiveMutex, OneThreadMayAcquireRepeatedlyButMustReleaseEveryLevel) {
  std::recursive_mutex mutex;
  mutex.lock();
  EXPECT_TRUE(mutex.try_lock());
  mutex.unlock();
  mutex.unlock();

  ASSERT_TRUE(mutex.try_lock());
  mutex.unlock();

  // recursive_mutex 记录同一线程的获取层数；每次成功 lock/try_lock 都须对应一次
  // unlock。它可兼容递归调用，但也容易掩盖锁层次设计问题，且最大深度由实现决定。
}

TEST(LockGuard, AdoptLockTakesResponsibilityForAnAlreadyOwnedMutex) {
  std::mutex mutex;
  mutex.lock();
  {
    const std::lock_guard<std::mutex> guard{mutex, std::adopt_lock};
    static_assert(!std::is_move_constructible_v<decltype(guard)>);
  }
  ASSERT_TRUE(mutex.try_lock());
  mutex.unlock();

  // adopt_lock 不执行 lock，只承诺当前线程已经拥有互斥量并让 guard 在析构时解锁。
  // 承诺不成立会导致未定义行为；它常与 std::lock 成对，而不是用于猜测锁状态。
}

TEST(ScopedLock, OppositeArgumentOrdersStillUseDeadlockAvoidance) {
  std::mutex first;
  std::mutex second;
  int value = 0;
  auto increment = [&](bool reverse) {
    for (int iteration = 0; iteration < 500; ++iteration) {
      if (reverse) {
        const std::scoped_lock guard{second, first};
        ++value;
      } else {
        const std::scoped_lock guard{first, second};
        ++value;
      }
    }
  };

  std::thread left{increment, false};
  std::thread right{increment, true};
  left.join();
  right.join();

  EXPECT_EQ(value, 1000);

  // scoped_lock 对多个互斥量使用免死锁算法，并在逆序析构时全部释放；仅靠逐个
  // lock_guard 无法处理相反锁序。所有参数仍须是不同的 Lockable 对象。
}

TEST(GenericLock, LockThenAdoptLetsSeparateGuardsOwnTheAcquiredMutexes) {
  std::mutex first;
  std::mutex second;

  std::lock(first, second);
  {
    const std::lock_guard<std::mutex> first_guard{first, std::adopt_lock};
    const std::lock_guard<std::mutex> second_guard{second, std::adopt_lock};
  }

  ASSERT_TRUE(first.try_lock());
  first.unlock();
  ASSERT_TRUE(second.try_lock());
  second.unlock();

  // std::lock 返回时全部锁已获取；若获取过程中抛异常，会解开本次已经获取的锁。
  // 随后的 adopt guard 把异常安全责任装入作用域，避免早退路径遗漏 unlock。
}

TEST(GenericTryLock, FailureIndexIdentifiesTheMutexAndEarlierLocksAreReleased) {
  std::mutex first;
  std::mutex second;
  std::mutex third;
  std::promise<void> second_locked;
  auto second_locked_future = second_locked.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  std::thread owner{[&] {
    const std::lock_guard<std::mutex> guard{second};
    second_locked.set_value();
    release_future.wait();
  }};
  second_locked_future.wait();

  EXPECT_EQ(std::try_lock(first, second, third), 1);
  ASSERT_TRUE(first.try_lock());
  first.unlock();
  ASSERT_TRUE(third.try_lock());
  third.unlock();

  release.set_value();
  owner.join();

  // try_lock 依次尝试，成功返回 -1，失败返回从 0 起的参数索引，并在返回前解锁
  // 本次已获取的较早对象；失败对象及尚未尝试对象都不归调用者所有。
}

TEST(LockTags, TagsSelectProtocolsButCarryNoRuntimeOwnershipEvidence) {
  static_assert(std::is_empty_v<std::defer_lock_t>);
  static_assert(std::is_empty_v<std::try_to_lock_t>);
  static_assert(std::is_empty_v<std::adopt_lock_t>);
  static_assert(!std::is_same_v<std::defer_lock_t, std::try_to_lock_t>);
  SUCCEED();

  // defer_lock、try_to_lock、adopt_lock 是重载选择标签，不记录具体 mutex 的状态。
  // 解锁未拥有的 mutex、递归锁普通 mutex、销毁仍被拥有的 mutex 都不可用测试执行。
}

}  // namespace
