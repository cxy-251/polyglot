// polyglot-covers:
// - cpp.stdlib.concurrency.unique-lock-deferred-lock-unlock-and-observers
// - cpp.stdlib.concurrency.unique-lock-try-adopt-release-and-preconditions
// - cpp.stdlib.concurrency.unique-lock-move-swap-and-ownership-transfer
// - cpp.stdlib.concurrency.unique-lock-invalid-operation-system-errors
// - cpp.stdlib.concurrency.timed-mutex-zero-duration-and-deadline-attempts
// - cpp.stdlib.concurrency.recursive-timed-mutex-reentrant-ownership
// - cpp.stdlib.concurrency.shared-mutex-concurrent-readers-exclusive-writer
// - cpp.stdlib.concurrency.shared-lock-defer-move-release-and-observers
// - cpp.stdlib.concurrency.shared-timed-mutex-zero-duration-attempt
// - cpp.stdlib.concurrency.timed-wait-spurious-failure-and-clock-traps

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <mutex>
#include <shared_mutex>
#include <system_error>
#include <thread>
#include <utility>

namespace {

TEST(UniqueLock, DeferredConstructionSeparatesAssociationFromOwnership) {
  std::mutex mutex;
  std::unique_lock<std::mutex> lock{mutex, std::defer_lock};

  EXPECT_EQ(lock.mutex(), &mutex);
  EXPECT_FALSE(lock.owns_lock());
  EXPECT_FALSE(static_cast<bool>(lock));
  lock.lock();
  EXPECT_TRUE(lock.owns_lock());
  lock.unlock();
  EXPECT_FALSE(lock.owns_lock());
  EXPECT_EQ(lock.mutex(), &mutex);

  // unique_lock 可关联 mutex 却暂不拥有它；unlock 只放弃所有权，不解除关联。
  // 这种状态让条件变量和通用锁算法能延后获取，但每次 lock 都须满足未拥有前置条件。
}

TEST(UniqueLock, TryAndAdoptConstructorsEncodeDifferentAcquisitionProtocols) {
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

  std::unique_lock<std::mutex> attempted{mutex, std::try_to_lock};
  EXPECT_FALSE(attempted.owns_lock());
  release.set_value();
  owner.join();

  mutex.lock();
  std::unique_lock<std::mutex> adopted{mutex, std::adopt_lock};
  EXPECT_TRUE(adopted.owns_lock());
  adopted.unlock();

  // try_to_lock 调用 try_lock 并允许无所有权结果；adopt_lock 完全不调用 lock，
  // 前置条件是当前线程已经拥有 mutex。两者都不会从 mutex 自身查询“谁是 owner”。
}

TEST(UniqueLock, ReleaseReturnsTheMutexWithoutUnlockingIt) {
  std::mutex mutex;
  mutex.lock();
  std::unique_lock<std::mutex> owner{mutex, std::adopt_lock};

  std::mutex* raw = owner.release();

  EXPECT_EQ(raw, &mutex);
  EXPECT_EQ(owner.mutex(), nullptr);
  EXPECT_FALSE(owner.owns_lock());
  raw->unlock();

  // release 放弃 RAII 句柄但故意不 unlock，调用者必须接手解锁责任；它不同于
  // unlock。若忽略返回指针，锁会泄漏并让其他线程永久阻塞。
}

TEST(UniqueLock, MoveAndSwapTransferAssociationAndOwnershipWithoutLocking) {
  std::mutex first_mutex;
  std::mutex second_mutex;
  std::unique_lock<std::mutex> first{first_mutex};
  std::unique_lock<std::mutex> second{second_mutex, std::defer_lock};

  swap(first, second);
  EXPECT_EQ(first.mutex(), &second_mutex);
  EXPECT_FALSE(first.owns_lock());
  EXPECT_EQ(second.mutex(), &first_mutex);
  EXPECT_TRUE(second.owns_lock());

  std::unique_lock<std::mutex> moved = std::move(second);
  EXPECT_EQ(second.mutex(), nullptr);
  EXPECT_FALSE(second.owns_lock());
  EXPECT_EQ(moved.mutex(), &first_mutex);
  EXPECT_TRUE(moved.owns_lock());

  // unique_lock 是可移动的所有权令牌；swap/move 不触碰底层 mutex 状态。移后对象
  // 不再关联 mutex，可安全析构但不能 lock，除非重新赋值一个有效句柄。
}

TEST(UniqueLockErrors, ReacquiringAnOwnedLockViolatesTheStateMachine) {
  std::mutex mutex;
  std::unique_lock<std::mutex> lock{mutex};

  EXPECT_THROW(lock.lock(), std::system_error);
  EXPECT_THROW(static_cast<void>(lock.try_lock()), std::system_error);
  lock.unlock();
  EXPECT_THROW(lock.unlock(), std::system_error);

  std::unique_lock<std::mutex> empty;
  EXPECT_THROW(empty.lock(), std::system_error);

  // unique_lock 会把“无关联”“已拥有”“未拥有”等非法操作报告为 system_error，
  // 但 adopt_lock 的虚假承诺仍可能直接导致未定义行为，不能依赖这些检查兜底。
}

TEST(TimedMutex, ZeroDurationAndCurrentDeadlineProvideNonSleepingAttempts) {
  std::timed_mutex mutex;
  std::promise<void> locked;
  auto locked_future = locked.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  std::thread owner{[&] {
    const std::lock_guard<std::timed_mutex> guard{mutex};
    locked.set_value();
    release_future.wait();
  }};
  locked_future.wait();

  EXPECT_FALSE(mutex.try_lock_for(std::chrono::milliseconds::zero()));
  EXPECT_FALSE(mutex.try_lock_until(std::chrono::steady_clock::now()));
  release.set_value();
  owner.join();
  ASSERT_TRUE(mutex.try_lock_for(std::chrono::milliseconds::zero()));
  mutex.unlock();

  // 相对超时由实现换算时钟，实际阻塞可长于请求；try_lock_for 还允许伪失败。
  // 测试使用零时长和显式事件，不用 sleep 猜测另一个线程何时持锁。
}

TEST(RecursiveTimedMutex, TimedAcquisitionAlsoTracksRecursiveDepth) {
  std::recursive_timed_mutex mutex;
  mutex.lock();
  EXPECT_TRUE(mutex.try_lock_for(std::chrono::milliseconds::zero()));
  mutex.unlock();
  mutex.unlock();

  // recursive_timed_mutex 合并递归层数与定时接口；同线程再次获取成功不代表其他
  // 线程能及时获得锁。每一层仍要释放，超时接口也不提供公平队列保证。
}

TEST(SharedMutex, MultipleReadersCoexistWhileExclusiveTryLockFails) {
  std::shared_mutex mutex;
  std::promise<void> first_locked;
  std::promise<void> second_locked;
  auto first_future = first_locked.get_future();
  auto second_future = second_locked.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  std::thread first{[&] {
    const std::shared_lock<std::shared_mutex> guard{mutex};
    first_locked.set_value();
    release_future.wait();
  }};
  std::thread second{[&] {
    const std::shared_lock<std::shared_mutex> guard{mutex};
    second_locked.set_value();
    release_future.wait();
  }};
  first_future.wait();
  second_future.wait();

  EXPECT_FALSE(mutex.try_lock());
  release.set_value();
  first.join();
  second.join();
  ASSERT_TRUE(mutex.try_lock());
  mutex.unlock();

  // lock_shared 允许多个读者，独占 lock 与任何共享/独占 owner 互斥。标准不保证
  // 读写公平，也不提供原子“共享升级为独占”；手工 unlock_shared 再 lock 会有窗口。
}

TEST(SharedLock, MoveAndReleaseMirrorUniqueLockForSharedOwnership) {
  std::shared_mutex mutex;
  std::shared_lock<std::shared_mutex> deferred{mutex, std::defer_lock};
  EXPECT_FALSE(deferred.owns_lock());
  deferred.lock();

  std::shared_lock<std::shared_mutex> moved = std::move(deferred);
  EXPECT_FALSE(deferred.owns_lock());
  EXPECT_EQ(deferred.mutex(), nullptr);
  EXPECT_TRUE(moved.owns_lock());
  EXPECT_EQ(moved.mutex(), &mutex);

  std::shared_mutex* raw = moved.release();
  EXPECT_FALSE(moved.owns_lock());
  EXPECT_EQ(moved.mutex(), nullptr);
  raw->unlock_shared();

  // shared_lock 管理的是共享所有权，状态机与 unique_lock 相似；release 后必须调用
  // unlock_shared 而不是 unlock。两种所有权令牌不可互相隐式转换。
}

TEST(SharedTimedMutex, TimedSharedAndExclusiveAttemptsRespectCurrentOwners) {
  std::shared_timed_mutex mutex;
  mutex.lock_shared();
  std::promise<bool> result;
  auto future = result.get_future();
  std::thread writer{[&] {
    const bool acquired =
        mutex.try_lock_for(std::chrono::milliseconds::zero());
    result.set_value(acquired);
    if (acquired) {
      mutex.unlock();
    }
  }};

  EXPECT_FALSE(future.get());
  writer.join();
  mutex.unlock_shared();
  ASSERT_TRUE(mutex.try_lock_shared_for(std::chrono::milliseconds::zero()));
  mutex.unlock_shared();

  // shared_timed_mutex 同时提供共享和独占定时接口。用哪个时钟、超时后的调度延迟
  // 及伪失败都不可作为业务正确性条件；超时应是可重试/降级结果。
}

}  // namespace
