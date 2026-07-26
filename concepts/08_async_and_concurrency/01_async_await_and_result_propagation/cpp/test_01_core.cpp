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

  EXPECT_EQ(result.get(), 42);
}

TEST(AsyncResultConcept, FutureGetRethrowsTheStoredException) {
  std::promise<int> producer;
  std::future<int> result = producer.get_future();

  producer.set_exception(std::make_exception_ptr(std::runtime_error{"failed"}));

  EXPECT_THROW(static_cast<void>(result.get()), std::runtime_error);
}

TEST(AsyncResultConcept, AsyncLaunchPolicyControlsExecutionMode) {
  auto deferred = std::async(std::launch::deferred, [] { return 42; });

  EXPECT_EQ(deferred.wait_for(std::chrono::seconds{0}), std::future_status::deferred);
  EXPECT_EQ(deferred.get(), 42);
}

TEST(AsyncResultConcept, FutureIsSingleConsumerButSharedFutureIsReusable) {
  std::promise<int> producer;
  std::shared_future<int> result = producer.get_future().share();
  producer.set_value(42);

  EXPECT_EQ(result.get(), 42);
  EXPECT_EQ(result.get(), 42);

  // 标准 future 不是 JavaScript Promise；普通 future::get 会消耗共享状态访问权。
}

}  // namespace
