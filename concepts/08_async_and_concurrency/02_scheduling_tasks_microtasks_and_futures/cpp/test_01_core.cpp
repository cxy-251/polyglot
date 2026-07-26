// 任务调度、微任务与 Future。
// 共同问题：同步代码与调度任务的先后关系；任务何时开始；完成回调何时运行；
// 调度器是否由语言统一规定。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_154_promise_future_shared_state_results_errors_and_waiting.cpp

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <future>
#include <thread>

namespace {

TEST(SchedulingConcept, DeferredAsyncStartsWhenResultIsRequested) {
  std::atomic<bool> ran{false};
  auto result = std::async(std::launch::deferred, [&ran] {
    ran = true;
    return 42;
  });

  EXPECT_FALSE(ran.load());
  EXPECT_EQ(result.get(), 42);
  EXPECT_TRUE(ran.load());
}

TEST(SchedulingConcept, ExplicitAsyncMayRunOnAnotherThread) {
  std::thread::id caller = std::this_thread::get_id();
  auto worker = std::async(std::launch::async, [] { return std::this_thread::get_id(); });

  EXPECT_NE(worker.get(), caller);
}

TEST(SchedulingConcept, PromiseMakesFutureReadyAtAnExplicitPoint) {
  std::promise<int> producer;
  auto result = producer.get_future();

  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::timeout);
  producer.set_value(42);
  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::ready);
}

TEST(SchedulingConcept, StandardCpp20DoesNotDefineAUniversalEventLoop) {
  // future 没有标准 then/microtask 队列；executor/sender-receiver 不属于锁定的 C++20 基线。
  SUCCEED();
}

}  // namespace
