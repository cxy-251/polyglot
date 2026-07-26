// polyglot-covers:
// - cpp.stdlib.concurrency.condition-variable-wait-unlock-relock-and-predicate-loop
// - cpp.stdlib.concurrency.condition-variable-notify-before-wait-and-lost-wakeup-avoidance
// - cpp.stdlib.concurrency.condition-variable-notify-one-notify-all-and-shared-state
// - cpp.stdlib.concurrency.condition-variable-timed-wait-status-and-final-predicate
// - cpp.stdlib.concurrency.condition-variable-any-basic-lockable-and-stop-token
// - cpp.stdlib.concurrency.notify-all-at-thread-exit-and-thread-local-destruction
// - cpp.stdlib.concurrency.condition-variable-native-handle-and-lifetime-preconditions

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <future>
#include <mutex>
#include <stop_token>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(ConditionVariable, PredicateWaitAtomicallyUnlocksAndRelocksTheMutex) {
  std::mutex mutex;
  std::condition_variable changed;
  bool ready = false;
  int payload = 0;
  std::promise<void> waiter_has_lock;
  auto waiter_has_lock_future = waiter_has_lock.get_future();

  std::thread waiter{[&] {
    std::unique_lock<std::mutex> lock{mutex};
    waiter_has_lock.set_value();
    changed.wait(lock, [&] { return ready; });

    // wait 返回时已经重新拥有同一把锁，因此这里读取普通对象没有数据竞争。
    EXPECT_TRUE(lock.owns_lock());
    EXPECT_EQ(lock.mutex(), &mutex);
    EXPECT_EQ(payload, 42);
  }};
  waiter_has_lock_future.wait();

  {
    // 若 wait 没有在进入等待状态时释放 mutex，生产者便不可能走到这里。
    const std::lock_guard<std::mutex> lock{mutex};
    payload = 42;
    ready = true;
  }
  changed.notify_one();
  waiter.join();

  // 谓词重载等价于 while (!pred()) wait(lock)，既处理伪唤醒，也把共享状态
  // 的判断放在 mutex 保护下。只等待“通知”而没有谓词，会丢失业务条件。
}

TEST(ConditionVariable, StatePredicateMakesNotificationBeforeWaitHarmless) {
  std::mutex mutex;
  std::condition_variable changed;
  bool ready = false;

  {
    const std::lock_guard<std::mutex> lock{mutex};
    ready = true;
  }
  changed.notify_one();  // 此刻没有 waiter，通知本身不会被保存。

  std::unique_lock<std::mutex> lock{mutex};
  int predicate_calls = 0;
  changed.wait(lock, [&] {
    ++predicate_calls;
    return ready;
  });

  EXPECT_EQ(predicate_calls, 1);
  EXPECT_TRUE(lock.owns_lock());

  // condition_variable 没有“积攒通知”的计数器；真正持久的是 mutex 保护的 ready。
  // 谓词初次即为 true 时不会阻塞，因此通知早于 wait 也不会形成 lost wakeup。
}

TEST(ConditionVariable, NotifyAllLetsEveryWaiterRecheckOneSharedGeneration) {
  std::mutex mutex;
  std::condition_variable changed;
  int generation = 0;
  std::atomic<int> entered{0};
  std::vector<int> observed(3, 0);
  std::vector<std::thread> waiters;

  for (int index = 0; index < 3; ++index) {
    waiters.emplace_back([&, index] {
      entered.fetch_add(1, std::memory_order_release);
      std::unique_lock<std::mutex> lock{mutex};
      changed.wait(lock, [&] { return generation >= 1; });
      observed[static_cast<std::size_t>(index)] = generation;
    });
  }

  while (entered.load(std::memory_order_acquire) != 3) {
    std::this_thread::yield();
  }
  {
    const std::lock_guard<std::mutex> lock{mutex};
    generation = 1;
  }
  changed.notify_all();

  for (auto& waiter : waiters) {
    waiter.join();
  }
  EXPECT_EQ(observed, (std::vector<int>{1, 1, 1}));

  // notify_all 只让所有 waiter 有资格竞争 mutex，并不让它们同时进入临界区；
  // 每个 waiter 取得锁后仍必须重查谓词。notify_one 选择哪个 waiter也未指定。
}

TEST(ConditionVariableTimeouts, StatusAndPredicateOverloadsAnswerDifferentQuestions) {
  std::mutex mutex;
  std::condition_variable changed;
  std::unique_lock<std::mutex> lock{mutex};

  const auto status =
      changed.wait_for(lock, std::chrono::milliseconds::zero());
  EXPECT_EQ(status, std::cv_status::timeout);
  EXPECT_TRUE(lock.owns_lock());

  bool ready = false;
  EXPECT_FALSE(changed.wait_until(
      lock, std::chrono::steady_clock::now(), [&] { return ready; }));
  ready = true;
  EXPECT_TRUE(changed.wait_for(
      lock, std::chrono::milliseconds::zero(), [&] { return ready; }));

  // 无谓词版本返回“截止时刻是否到期”；谓词版本最终再判断一次条件，返回条件
  // 是否成立。即便 deadline 已过，谓词初次为 true 也会立即返回 true。
}

class CountingLock {
 public:
  explicit CountingLock(std::mutex& mutex) : mutex_{mutex} {
    lock();
  }

  void lock() {
    mutex_.lock();
    ++lock_calls;
  }

  void unlock() {
    ++unlock_calls;
    mutex_.unlock();
  }

  int lock_calls = 0;
  int unlock_calls = 0;

 private:
  std::mutex& mutex_;
};

TEST(ConditionVariableAny, UserSuppliedBasicLockableIsUnlockedAndRelocked) {
  std::mutex mutex;
  std::condition_variable_any changed;
  bool ready = false;
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  int lock_calls = 0;
  int unlock_calls = 0;

  std::thread waiter{[&] {
    CountingLock lock{mutex};
    entered.set_value();
    changed.wait(lock, [&] { return ready; });
    lock_calls = lock.lock_calls;
    unlock_calls = lock.unlock_calls;
    lock.unlock();
  }};
  entered_future.wait();
  {
    const std::lock_guard<std::mutex> lock{mutex};
    ready = true;
  }
  changed.notify_one();
  waiter.join();

  EXPECT_EQ(lock_calls, 2);    // 构造时一次，wait 重新上锁一次。
  EXPECT_EQ(unlock_calls, 1);  // wait 进入阻塞状态时一次。

  // condition_variable 只接受 unique_lock<mutex>；any 版本通过调用用户 Lock 的
  // lock/unlock 换取泛化能力。自定义锁仍须自行保证谓词共享状态的同步正确性。
}

TEST(ConditionVariableAny, StopTokenInterruptsAPredicateWaitWithoutNotification) {
  std::mutex mutex;
  std::condition_variable_any changed;
  bool ready = false;
  std::promise<void> waiting;
  auto waiting_future = waiting.get_future();
  std::promise<bool> result;
  auto result_future = result.get_future();

  std::jthread worker{[&](std::stop_token token) {
    std::unique_lock<std::mutex> lock{mutex};
    waiting.set_value();
    result.set_value(changed.wait(lock, token, [&] { return ready; }));
  }};
  waiting_future.wait();
  worker.request_stop();

  EXPECT_FALSE(result_future.get());
  worker.join();

  // C++20 的 condition_variable_any 可把 stop_token 纳入等待。返回 false 表示
  // stop 被请求而谓词仍不成立；停止请求是协作信号，不会强行终止线程。
}

struct ThreadExitProbe {
  ~ThreadExitProbe() {
    destroyed->store(true, std::memory_order_relaxed);
  }

  std::atomic<bool>* destroyed = nullptr;
};

TEST(ConditionVariableThreadExit, NotificationOccursAfterThreadLocalDestruction) {
  std::mutex mutex;
  std::condition_variable finished;
  bool exiting = false;
  std::atomic<bool> thread_local_destroyed{false};

  std::thread worker{[&] {
    thread_local ThreadExitProbe probe;
    probe.destroyed = &thread_local_destroyed;

    std::unique_lock<std::mutex> lock{mutex};
    exiting = true;
    std::notify_all_at_thread_exit(finished, std::move(lock));
    // lock 的所有权已经转入库中；线程退出时先销毁 thread_local，再 unlock+notify。
  }};

  std::unique_lock<std::mutex> lock{mutex};
  finished.wait(lock, [&] { return exiting; });
  EXPECT_TRUE(thread_local_destroyed.load(std::memory_order_relaxed));
  lock.unlock();
  worker.join();

  // 若普通 notify 后线程仍继续清理，等待方可能把“状态已发布”误当作“线程已退出”。
  // notify_all_at_thread_exit 专门把解锁和通知推迟到线程局部对象销毁之后。
}

TEST(ConditionVariableProperties, NativeHandleExistsButItsMeaningIsImplementationDefined) {
  using Condition = std::condition_variable;
  static_assert(std::is_standard_layout_v<Condition>);
  static_assert(!std::is_copy_constructible_v<Condition>);
  static_assert(!std::is_copy_assignable_v<Condition>);

  Condition condition;
  [[maybe_unused]] Condition::native_handle_type handle =
      condition.native_handle();
  SUCCEED();

  // native_handle_type 及其值都由实现定义，只适合明确依赖平台 API 的适配层。
  // 析构前必须确保已无阻塞 waiter；通知过但尚在竞争 mutex 的线程不再阻塞于 cv。
}

}  // namespace
