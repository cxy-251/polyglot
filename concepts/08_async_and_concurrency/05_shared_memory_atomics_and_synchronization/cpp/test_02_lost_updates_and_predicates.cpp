// 丢失更新、条件谓词与同步边界。
// 共同问题：运行时锁是否自动保护复合操作；条件通知能否替代状态谓词；
// 发布数据需要哪一个明确同步点。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_157_atomic_types_exchange_compare_exchange_and_fetch_operations.cpp
// polyglot-related: languages/cpp/standard_library/17_concurrency/
// polyglot-related+: test_158_atomic_wait_notify_and_atomic_ref_aliasing.cpp

#include <gtest/gtest.h>

#include <atomic>
#include <thread>

namespace {

TEST(AtomicCoordinationConcept, AtomicWaitUsesReleaseAcquirePublication) {
  int payload = 0;
  int observed = 0;
  std::atomic<int> state{0};
  std::thread consumer{[&] {
    state.wait(0, std::memory_order_acquire);
    observed = payload;
  }};
  std::thread producer{[&] {
    payload = 42;
    state.store(1, std::memory_order_release);
    state.notify_one();
  }};

  producer.join();
  consumer.join();

  EXPECT_EQ(observed, 42);

  // release store 与读到 1 的 acquire wait 建立 happens-before；notify 只负责唤醒，
  // 真正发布状态的是 atomic value 与 memory order。
}

TEST(AtomicCoordinationConcept, CompareExchangeUpdatesExpectedOnFailure) {
  std::atomic<int> value{2};
  int expected = 1;

  EXPECT_FALSE(value.compare_exchange_strong(expected, 3));
  EXPECT_EQ(expected, 2);
  EXPECT_EQ(value.load(), 2);

  EXPECT_TRUE(value.compare_exchange_strong(expected, 3));
  EXPECT_EQ(value.load(), 3);

  // CAS 循环必须使用失败后被更新的 expected，不能假定比较失败不修改参数。
}

}  // namespace
