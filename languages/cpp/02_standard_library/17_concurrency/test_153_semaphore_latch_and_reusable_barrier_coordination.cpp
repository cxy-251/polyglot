// polyglot-covers:
// - cpp.stdlib.concurrency.counting-semaphore-release-acquire-count-and-max
// - cpp.stdlib.concurrency.binary-semaphore-try-and-timed-acquisition
// - cpp.stdlib.concurrency.semaphore-release-acquire-synchronization
// - cpp.stdlib.concurrency.latch-count-down-wait-and-single-use
// - cpp.stdlib.concurrency.latch-arrive-and-wait-synchronization
// - cpp.stdlib.concurrency.barrier-reusable-phases-and-completion-function
// - cpp.stdlib.concurrency.barrier-arrival-token-split-arrive-and-wait
// - cpp.stdlib.concurrency.barrier-arrive-and-drop-adjusts-later-phases

#include <gtest/gtest.h>

#include <atomic>
#include <barrier>
#include <chrono>
#include <future>
#include <latch>
#include <semaphore>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(CountingSemaphore, ReleaseAddsPermitsAndAcquireConsumesThem) {
  std::counting_semaphore<5> permits{0};
  static_assert(std::counting_semaphore<5>::max() >= 5);

  EXPECT_FALSE(permits.try_acquire());
  permits.release(3);
  EXPECT_TRUE(permits.try_acquire());
  EXPECT_TRUE(permits.try_acquire());
  permits.acquire();
  EXPECT_FALSE(permits.try_acquire());

  // semaphore 管理的是匿名 permit 数量，不记录线程所有权；release(3) 可由任意
  // 线程补入三个 permit。计数超过 max 或 acquire 后永不归还都是调用者错误。
}

TEST(BinarySemaphore, ZeroDurationAttemptsDoNotNeedSchedulingDelays) {
  std::binary_semaphore gate{0};

  EXPECT_FALSE(gate.try_acquire());
  EXPECT_FALSE(gate.try_acquire_for(std::chrono::milliseconds::zero()));
  EXPECT_FALSE(gate.try_acquire_until(std::chrono::steady_clock::now()));
  gate.release();
  EXPECT_TRUE(gate.try_acquire());
  EXPECT_FALSE(gate.try_acquire());

  // binary_semaphore 是 counting_semaphore<1> 的别名。定时获取允许伪失败，
  // 测试只用零时长表达“不阻塞尝试”，不把调度耗时当作语义断言。
}

TEST(CountingSemaphore, ReleaseSynchronizesPayloadWithSuccessfulAcquire) {
  std::binary_semaphore ready{0};
  int payload = 0;
  std::thread producer{[&] {
    payload = 91;
    ready.release();
  }};

  ready.acquire();
  EXPECT_EQ(payload, 91);
  producer.join();

  // 向 semaphore 的 release 与成功取得该 permit 的 acquire 建立同步，因此普通
  // payload 的写入可见。try_acquire 的失败没有同步效果，不能借此读取共享数据。
}

TEST(Latch, CountDownOpensASingleUseGateForAllWaiters) {
  std::latch ready{2};
  static_assert(std::latch::max() >= 2);
  EXPECT_FALSE(ready.try_wait());

  ready.count_down();
  EXPECT_FALSE(ready.try_wait());
  ready.count_down();
  ready.wait();
  EXPECT_TRUE(ready.try_wait());

  // latch 的计数只能下降；到零后 wait 立即返回，却不能 reset 或进入下一阶段。
  // count_down 的 update 超过当前计数违反前置条件，不能用测试执行这种错误。
}

TEST(Latch, ArriveAndWaitPublishesEveryWorkersPriorWrites) {
  std::latch rendezvous{3};
  std::vector<int> values(3, 0);
  std::vector<int> sums(3, 0);
  std::vector<std::thread> workers;

  for (int index = 0; index < 3; ++index) {
    workers.emplace_back([&, index] {
      values[static_cast<std::size_t>(index)] = index + 1;
      rendezvous.arrive_and_wait();
      sums[static_cast<std::size_t>(index)] =
          values[0] + values[1] + values[2];
    });
  }
  for (auto& worker : workers) {
    worker.join();
  }

  EXPECT_EQ(sums, (std::vector<int>{6, 6, 6}));

  // 把计数降为零的操作 strongly happens-before 所有被解阻塞 wait 的返回；
  // 因此每个线程越过门闩后都能读取其他线程在到达前写入的不同元素。
}

TEST(Barrier, CompletionRunsOncePerReusablePhaseBeforeWorkersContinue) {
  std::atomic<int> completed_phases{0};
  auto completion = [&]() noexcept {
    completed_phases.fetch_add(1, std::memory_order_relaxed);
  };
  std::barrier phase{3, completion};
  static_assert(decltype(phase)::max() >= 3);
  std::vector<int> observations(6, 0);
  std::vector<std::thread> workers;

  for (int index = 0; index < 3; ++index) {
    workers.emplace_back([&, index] {
      phase.arrive_and_wait();
      observations[static_cast<std::size_t>(index)] =
          completed_phases.load(std::memory_order_relaxed);
      phase.arrive_and_wait();
      observations[static_cast<std::size_t>(index + 3)] =
          completed_phases.load(std::memory_order_relaxed);
    });
  }
  for (auto& worker : workers) {
    worker.join();
  }

  EXPECT_EQ(observations, (std::vector<int>{1, 1, 1, 2, 2, 2}));

  // barrier 与 latch 不同，会在 completion 完成后恢复 expected count 并开始下一
  // phase。completion 必须 noexcept，且其结束 strongly happens-before waiter 返回。
}

TEST(Barrier, ArrivalTokenSeparatesArrivalFromPotentiallyBlockingWait) {
  std::barrier phase{2};
  std::promise<void> arrived;
  auto arrived_future = arrived.get_future();
  std::promise<void> may_wait;
  auto may_wait_future = may_wait.get_future().share();
  std::atomic<bool> crossed{false};

  std::thread worker{[&] {
    auto token = phase.arrive();
    arrived.set_value();
    may_wait_future.wait();
    phase.wait(std::move(token));
    crossed.store(true, std::memory_order_relaxed);
  }};
  arrived_future.wait();
  EXPECT_FALSE(crossed.load(std::memory_order_relaxed));

  phase.arrive_and_wait();
  may_wait.set_value();
  worker.join();
  EXPECT_TRUE(crossed.load(std::memory_order_relaxed));

  // arrive 只减少计数并返回 move-only phase token，不一定阻塞；wait 可稍后甚至由
  // 另一线程接收 token 后完成。忽略 [[nodiscard]] token 会失去等待该 phase 的入口。
}

TEST(Barrier, ArriveAndDropPermanentlyShrinksLaterPhaseParticipation) {
  std::barrier phase{3};
  std::atomic<int> survivors{0};

  std::thread leaving{[&] { phase.arrive_and_drop(); }};
  std::thread first{[&] {
    phase.arrive_and_wait();
    phase.arrive_and_wait();
    survivors.fetch_add(1, std::memory_order_relaxed);
  }};
  std::thread second{[&] {
    phase.arrive_and_wait();
    phase.arrive_and_wait();
    survivors.fetch_add(1, std::memory_order_relaxed);
  }};

  leaving.join();
  first.join();
  second.join();
  EXPECT_EQ(survivors.load(std::memory_order_relaxed), 2);

  // arrive_and_drop 同时完成当前 phase 的一次到达，并永久把后续 phase 的初始计数
  // 减一；离开者以后不得再次参与，否则会破坏每阶段预期参与者数量。
}

TEST(SynchronizationPrimitiveProperties, ObjectsAreSharedButNotCopyableHandles) {
  static_assert(!std::is_copy_constructible_v<std::binary_semaphore>);
  static_assert(!std::is_copy_constructible_v<std::latch>);
  static_assert(!std::is_copy_constructible_v<std::barrier<>>);
  static_assert(!std::is_move_constructible_v<std::latch>);
  static_assert(!std::is_move_constructible_v<std::barrier<>>);
  SUCCEED();

  // 这些对象通常由引用共享；析构时仍有等待者或并发成员调用会破坏生命周期前置
  // 条件。RAII 只管理对象寿命，不会自动让后台线程停止等待。
}

}  // namespace
