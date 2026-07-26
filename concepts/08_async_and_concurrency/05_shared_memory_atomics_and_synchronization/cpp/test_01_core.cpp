// 共享内存、原子操作与同步。
// 共同问题：并发工作如何共享状态；互斥和条件通知保证什么；是否提供原子读改写；
// 消息传递与共享内存的边界在哪里。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <atomic>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <vector>

namespace {

TEST(SynchronizationConcept, AtomicFetchAddIsOneReadModifyWriteOperation) {
  std::atomic<int> counter{0};
  std::thread first{[&counter] {
    for (int index = 0; index < 500; ++index) {
      counter.fetch_add(1);
    }
  }};
  std::thread second{[&counter] {
    for (int index = 0; index < 500; ++index) {
      counter.fetch_add(1);
    }
  }};

  first.join();
  second.join();

  EXPECT_EQ(counter.load(), 1000);
}

TEST(SynchronizationConcept, MutexProtectsACompoundContainerOperation) {
  std::mutex mutex;
  std::vector<int> values;
  auto append = [&mutex, &values](int value) {
    std::lock_guard lock{mutex};
    values.push_back(value);
  };
  std::thread first{append, 1};
  std::thread second{append, 2};

  first.join();
  second.join();

  EXPECT_EQ(values.size(), 2U);
}

TEST(SynchronizationConcept, ConditionVariableWaitAlwaysRechecksPredicate) {
  std::mutex mutex;
  std::condition_variable condition;
  bool ready = false;
  bool observed = false;
  std::thread worker{[&] {
    std::unique_lock lock{mutex};
    condition.wait(lock, [&ready] { return ready; });
    observed = true;
  }};

  {
    std::lock_guard lock{mutex};
    ready = true;
  }
  condition.notify_one();
  worker.join();

  EXPECT_TRUE(observed);
}

TEST(SynchronizationConcept, ReleaseAndAcquirePublishEarlierWrites) {
  int payload = 0;
  std::atomic<bool> published{false};
  std::thread producer{[&] {
    payload = 42;
    published.store(true, std::memory_order_release);
  }};
  std::thread consumer{[&] {
    while (!published.load(std::memory_order_acquire)) {
    }
    EXPECT_EQ(payload, 42);
  }};

  producer.join();
  consumer.join();
}

}  // namespace
