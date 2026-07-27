// ready queue、完成回调与显式执行边界。
// 共同问题：已经完成的结果何时通知后来观察者；同一队列是否保持登记顺序；
// 创建结果对象是否等同于启动工作。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_156_packaged_task_invocation_reset_and_thread_exit_readiness.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <type_traits>

namespace {

TEST(SchedulingBoundaryConcept, PackagedTaskDoesNotRunUntilExplicitInvocation) {
  int calls = 0;
  std::packaged_task<int()> task{[&calls] {
    ++calls;
    return 42;
  }};
  std::future<int> result = task.get_future();

  EXPECT_EQ(calls, 0);
  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::timeout);

  task();

  EXPECT_EQ(calls, 1);
  EXPECT_EQ(result.get(), 42);
}

TEST(SchedulingBoundaryConcept, FutureHasWaitingButNoStandardContinuationQueue) {
  std::promise<int> producer;
  std::future<int> result = producer.get_future();

  static_assert(std::is_same_v<decltype(result.wait()), void>);
  producer.set_value(7);
  result.wait();
  EXPECT_EQ(result.get(), 7);

  // C++20 future 没有 then/callback 或语言统一 event loop；执行发生在显式调用、
  // std::launch 策略或外部 scheduler 中，不能套用 JavaScript microtask 顺序。
}

}  // namespace
