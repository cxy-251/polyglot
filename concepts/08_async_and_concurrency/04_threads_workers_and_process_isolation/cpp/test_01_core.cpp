// 线程、Worker 与进程隔离。
// 共同问题：并发工作运行在哪里；参数如何进入工作单元；调用方如何等待结果；
// 工作单元是否共享对象、地址空间或运行时状态。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_147_thread_creation_arguments_ids_join_detach_and_this_thread.cpp

#include <gtest/gtest.h>

#include <functional>
#include <future>
#include <thread>

namespace {

TEST(ThreadIsolationConcept, ThreadHasItsOwnExecutionThreadAndJoinWaits) {
  std::thread::id caller = std::this_thread::get_id();
  std::thread::id worker_id;
  std::thread worker{[&worker_id] { worker_id = std::this_thread::get_id(); }};

  worker.join();

  EXPECT_NE(worker_id, caller);
  EXPECT_FALSE(worker.joinable());
}

TEST(ThreadIsolationConcept, ThreadArgumentsAreCopiedUnlessReferenceIsExplicit) {
  int value = 1;
  std::promise<int> copy_result;
  auto copied_value = copy_result.get_future();
  std::thread copied{[&copy_result](int local) {
    local = 42;
    copy_result.set_value(local);
  }, value};
  copied.join();
  EXPECT_EQ(copied_value.get(), 42);
  EXPECT_EQ(value, 1);

  std::thread referenced{[](int& shared) { shared = 42; }, std::ref(value)};
  referenced.join();
  EXPECT_EQ(value, 42);
}

TEST(ThreadIsolationConcept, JthreadDestructorJoinsOwnedThread) {
  std::promise<int> producer;
  auto result = producer.get_future();

  {
    std::jthread worker{[&producer] { producer.set_value(42); }};
    EXPECT_TRUE(worker.joinable());
  }

  EXPECT_EQ(result.get(), 42);
}

}  // namespace
