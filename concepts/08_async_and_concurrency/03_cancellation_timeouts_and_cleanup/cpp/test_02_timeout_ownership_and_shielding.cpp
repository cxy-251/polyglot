// 超时所有权、底层取消与屏蔽。
// 共同问题：等待超时是否取消底层工作；取消完成前是否等待清理；
// 调用方能否只取消当前等待而保留共享任务。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_148_stop_token_source_callback_and_jthread_cancellation.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <string>
#include <thread>
#include <vector>

namespace {

struct CleanupMarker {
  std::vector<std::string>& events;
  ~CleanupMarker() {
    events.push_back("cleanup");
  }
};

TEST(CancellationOwnershipConcept, JthreadDestructorRequestsStopThenJoins) {
  std::vector<std::string> events;
  std::promise<void> started;
  std::future<void> started_signal = started.get_future();

  {
    std::jthread worker{[&](std::stop_token token) {
      CleanupMarker cleanup{events};
      events.push_back("started");
      started.set_value();
      while (!token.stop_requested()) {
        std::this_thread::yield();
      }
      events.push_back("stop observed");
    }};
    started_signal.get();
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{"started", "stop observed", "cleanup"}));

  // jthread 拥有线程：析构会 request_stop 再 join；工作仍须主动观察 token，RAII 才在
  // 实际函数退出时运行。
}

TEST(CancellationOwnershipConcept, FutureTimeoutDoesNotCancelUnderlyingWork) {
  std::promise<void> started;
  std::promise<void> release;
  std::future<void> release_signal = release.get_future();
  auto result = std::async(
      std::launch::async,
      [&started, signal = std::move(release_signal)]() mutable {
        started.set_value();
        signal.get();
        return 42;
      });

  started.get_future().get();
  EXPECT_EQ(result.wait_for(std::chrono::seconds{0}), std::future_status::timeout);

  release.set_value();
  EXPECT_EQ(result.get(), 42);

  // wait_for timeout 只观察共享状态；它不会向 std::async 工作发送 stop_token。
}

}  // namespace
