// 取消、超时与清理。
// 共同问题：取消是否会强制停止工作；超时如何报告；被取消路径是否仍执行清理；
// 取消由运行时、协作协议还是所有权机制触发。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_148_stop_token_source_callback_and_jthread_cancellation.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <stop_token>
#include <type_traits>

namespace {

TEST(CancellationConcept, StopRequestIsCooperativeAndObservable) {
  std::stop_source source;
  std::stop_token token = source.get_token();

  EXPECT_FALSE(token.stop_requested());
  EXPECT_TRUE(source.request_stop());
  EXPECT_TRUE(token.stop_requested());
  EXPECT_FALSE(source.request_stop());
}

TEST(CancellationConcept, StopCallbackRunsWhenStopIsRequested) {
  std::stop_source source;
  bool callback_ran = false;
  std::stop_callback callback{source.get_token(), [&callback_ran] { callback_ran = true; }};

  source.request_stop();

  EXPECT_TRUE(callback_ran);
}

TEST(CancellationConcept, FutureTimeoutOnlyObservesReadiness) {
  std::promise<int> producer;
  auto result = producer.get_future();

  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::timeout);
  producer.set_value(42);
  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::ready);
}

struct NoThrowCleanup {
  ~NoThrowCleanup() noexcept = default;
};

TEST(CancellationConcept, DestructorsCannotSuppressCancellationOrTimeout) {
  static_assert(std::is_nothrow_destructible_v<NoThrowCleanup>);

  // stop_token 只传递请求，不会像 Python CancelledError 那样注入控制流。
  // RAII 仍可在实际作用域退出时清理，但析构函数不能决定是否继续传播取消或超时。
  SUCCEED();
}

}  // namespace
