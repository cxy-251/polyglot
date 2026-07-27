// 异步等待与结果传播。
// 共同问题：异步函数调用何时开始执行；await 如何取得结果；失败如何传播；
// 多个结果如何组合。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/cpp/language/test_021_coroutines_promise_awaiter_and_generator.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <stdexcept>

namespace {

TEST(AsyncResultConcept, FutureGetReturnsTheProducedValue) {
  std::promise<int> producer;
  std::future<int> result = producer.get_future();

  producer.set_value(42);

  EXPECT_TRUE(result.valid());
  EXPECT_EQ(result.get(), 42);
  EXPECT_FALSE(result.valid());

  // future::get 是单消费者操作：它取得结果后释放当前 future 对共享状态的访问权。
}

TEST(AsyncResultConcept, FutureGetRethrowsTheStoredException) {
  std::promise<int> producer;
  std::future<int> result = producer.get_future();

  producer.set_exception(std::make_exception_ptr(std::runtime_error{"failed"}));

  EXPECT_THROW(static_cast<void>(result.get()), std::runtime_error);
}

TEST(AsyncResultConcept, AsyncLaunchPolicyControlsExecutionMode) {
  auto deferred = std::async(std::launch::deferred, [] { return 42; });
  std::promise<void> started;
  std::promise<void> release;
  std::future<void> release_signal = release.get_future();
  auto asynchronous = std::async(
      std::launch::async,
      [&started, signal = std::move(release_signal)]() mutable {
        started.set_value();
        signal.get();
        return 7;
      });

  EXPECT_EQ(deferred.wait_for(std::chrono::seconds{0}), std::future_status::deferred);
  started.get_future().get();
  release.set_value();

  EXPECT_EQ(deferred.get(), 42);
  EXPECT_EQ(asynchronous.get(), 7);

  // deferred 直到 wait/get 才在等待线程执行；async 要求在独立执行线程启动。事件握手
  // 明确控制边界，不用 sleep 猜测调度时机。
}

TEST(AsyncResultConcept, FutureIsSingleConsumerButSharedFutureIsReusable) {
  std::promise<int> producer;
  std::shared_future<int> result = producer.get_future().share();
  producer.set_value(42);

  EXPECT_EQ(result.get(), 42);
  EXPECT_EQ(result.get(), 42);

  // shared_future 可被多个观察者重复读取；它仍不是自带 then/await 调度的 JavaScript
  // Promise，也不是由 promise_type 定制的 C++ coroutine return object。
}

}  // namespace
