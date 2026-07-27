// 并发结果、异常与数据传输边界。
// 共同问题：工作单元失败如何回到调用方；普通对象是共享、复制还是序列化；
// 所有者如何确认工作单元已经结束。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_147_thread_creation_arguments_ids_join_detach_and_this_thread.cpp
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_154_promise_future_shared_state_results_errors_and_waiting.cpp

#include <gtest/gtest.h>

#include <future>
#include <stdexcept>
#include <thread>

namespace {

TEST(ThreadResultConcept, AsyncFutureRethrowsWorkerExceptionToOwner) {
  auto result = std::async(std::launch::async, []() -> int {
    throw std::runtime_error{"worker failed"};
  });

  EXPECT_THROW(static_cast<void>(result.get()), std::runtime_error);
}

TEST(ThreadResultConcept, ThreadCanObserveTheSameObjectAddress) {
  int value = 1;
  const int* observed_address = nullptr;
  std::thread worker{[&] {
    observed_address = &value;
    value = 42;
  }};

  worker.join();

  EXPECT_EQ(observed_address, &value);
  EXPECT_EQ(value, 42);

  // std::thread 共享地址空间；join 建立完成同步。C++20 标准库没有进程/Worker 与
  // 结构化克隆边界，跨进程创建和 IPC 需要平台或第三方 API。
}

}  // namespace
