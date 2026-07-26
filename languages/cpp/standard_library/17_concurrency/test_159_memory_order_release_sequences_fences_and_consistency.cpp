// polyglot-covers:
// - cpp.stdlib.concurrency.memory-order-relaxed-atomicity-and-modification-order
// - cpp.stdlib.concurrency.memory-order-release-acquire-synchronizes-payload
// - cpp.stdlib.concurrency.release-sequence-relaxed-rmw-and-acquire-load
// - cpp.stdlib.concurrency.memory-order-seq-cst-single-total-order
// - cpp.stdlib.concurrency.memory-order-consume-dependency-and-kill-dependency
// - cpp.stdlib.concurrency.atomic-thread-fence-release-acquire-pattern
// - cpp.stdlib.concurrency.atomic-signal-fence-compiler-ordering-only
// - cpp.stdlib.concurrency.memory-order-operation-validity-and-common-traps

#include <gtest/gtest.h>

#include <atomic>
#include <barrier>
#include <thread>
#include <vector>

namespace {

TEST(MemoryOrderRelaxed, ReadModifyWriteIsAtomicWithoutPublishingOtherObjects) {
  std::atomic<int> counter{0};
  std::vector<std::thread> workers;
  for (int worker = 0; worker < 4; ++worker) {
    workers.emplace_back([&] {
      for (int iteration = 0; iteration < 1000; ++iteration) {
        counter.fetch_add(1, std::memory_order_relaxed);
      }
    });
  }
  for (auto& worker : workers) {
    worker.join();
  }
  EXPECT_EQ(counter.load(std::memory_order_relaxed), 4000);

  // relaxed 仍保证每次 RMW 不可分割，并让单个 atomic 的修改形成一致 modification
  // order；它不为其他普通对象建立 happens-before，不能用计数值发布关联 payload。
}

TEST(MemoryOrderAcquireRelease, ReleaseStorePublishesPriorWritesToAcquireLoad) {
  std::atomic<bool> ready{false};
  int payload = 0;
  int observed = 0;

  std::thread producer{[&] {
    payload = 42;
    ready.store(true, std::memory_order_release);
  }};
  std::thread consumer{[&] {
    while (!ready.load(std::memory_order_acquire)) {
      std::this_thread::yield();
    }
    observed = payload;
  }};
  producer.join();
  consumer.join();
  EXPECT_EQ(observed, 42);

  // acquire load 读到 release store 写入的值后，两者 synchronizes-with；producer
  // 之前的普通写入因而 happens-before consumer 的读取，不构成数据竞争。
}

TEST(MemoryOrderAcquireRelease, RelaxedRmwCanExtendAReleaseSequence) {
  std::atomic<int> sequence{0};
  int payload = 0;
  int observed = 0;

  std::thread producer{[&] {
    payload = 73;
    sequence.store(1, std::memory_order_release);
  }};
  std::thread relay{[&] {
    while (sequence.load(std::memory_order_relaxed) != 1) {
      std::this_thread::yield();
    }
    sequence.fetch_add(1, std::memory_order_relaxed);
  }};
  std::thread consumer{[&] {
    while (sequence.load(std::memory_order_acquire) < 2) {
      std::this_thread::yield();
    }
    observed = payload;
  }};
  producer.join();
  relay.join();
  consumer.join();
  EXPECT_EQ(observed, 73);

  // release store 后连续的原子 RMW 属于其 release sequence；acquire 读到 relay 的
  // 值仍与头部 release 同步。普通 store 会截断该关系，不能随意替换 fetch_add。
}

TEST(MemoryOrderSequentialConsistency, StoreThenLoadPatternCannotReadBothZeros) {
  std::atomic<int> left{0};
  std::atomic<int> right{0};
  int left_observed = -1;
  int right_observed = -1;
  std::barrier start{3};

  std::thread first{[&] {
    start.arrive_and_wait();
    left.store(1, std::memory_order_seq_cst);
    left_observed = right.load(std::memory_order_seq_cst);
  }};
  std::thread second{[&] {
    start.arrive_and_wait();
    right.store(1, std::memory_order_seq_cst);
    right_observed = left.load(std::memory_order_seq_cst);
  }};
  start.arrive_and_wait();
  first.join();
  second.join();

  EXPECT_FALSE(left_observed == 0 && right_observed == 0);

  // seq_cst 操作除 acquire/release 约束外还进入一个全局单一总序；两个 load 都排在
  // 对方 store 之前，会与各线程内“本方 store 先于 load”的顺序形成循环，故不可能。
}

struct PublishedNode {
  int value;
};

TEST(MemoryOrderConsume, AddressDependencyCarriesPublishedObjectInitialization) {
  PublishedNode node{0};
  std::atomic<PublishedNode*> published{nullptr};
  int observed = 0;

  std::thread producer{[&] {
    node.value = 29;
    published.store(&node, std::memory_order_release);
  }};
  std::thread consumer{[&] {
    PublishedNode* pointer = nullptr;
    while (pointer == nullptr) {
      pointer = published.load(std::memory_order_consume);
    }
    observed = pointer->value;
  }};
  producer.join();
  consumer.join();
  EXPECT_EQ(observed, 29);

  PublishedNode* pointer = &node;
  EXPECT_EQ(std::kill_dependency(pointer), pointer);

  // consume 只沿从读出值传播的 dependency ordering 约束后续操作；kill_dependency
  // 显式切断依赖。现实编译器通常把 consume 提升为 acquire，代码不宜依赖更弱优化。
}

TEST(AtomicThreadFence, ReleaseAndAcquireFencesCanSynchronizeRelaxedFlagAccess) {
  std::atomic<bool> ready{false};
  int payload = 0;
  int observed = 0;

  std::thread producer{[&] {
    payload = 101;
    std::atomic_thread_fence(std::memory_order_release);
    ready.store(true, std::memory_order_relaxed);
  }};
  std::thread consumer{[&] {
    while (!ready.load(std::memory_order_relaxed)) {
      std::this_thread::yield();
    }
    std::atomic_thread_fence(std::memory_order_acquire);
    observed = payload;
  }};
  producer.join();
  consumer.join();
  EXPECT_EQ(observed, 101);

  // fence 不携带值，必须借助 relaxed store/load 的 reads-from 关系连接两端。把 acquire
  // fence 放到 flag load 之前，或 release fence 放到 flag store 之后，都不能发布数据。
}

TEST(AtomicSignalFence, OnlyConstrainsCompilerOrderingAroundSignalHandlers) {
  int local = 1;
  std::atomic_signal_fence(std::memory_order_release);
  local = 2;
  std::atomic_signal_fence(std::memory_order_acquire);
  EXPECT_EQ(local, 2);

  // atomic_signal_fence 只限制同一线程与信号处理器之间的编译器重排，不发出跨线程
  // 硬件 fence。普通线程同步必须用 atomic_thread_fence 或带内存序的原子操作。
}

TEST(MemoryOrderRules, OrdersAreOperationSpecificNotGeneralPerformanceFlags) {
  std::atomic<int> value{1};
  value.store(2, std::memory_order_release);
  EXPECT_EQ(value.load(std::memory_order_acquire), 2);
  EXPECT_EQ(value.exchange(3, std::memory_order_acq_rel), 2);

  int expected = 3;
  EXPECT_TRUE(value.compare_exchange_strong(
      expected, 4, std::memory_order_acq_rel, std::memory_order_acquire));

  // load 不允许 release/acq_rel，store 不允许 consume/acquire/acq_rel；CAS 的 failure
  // order 还不能是 release/acq_rel 或强于 success。违反这些前置条件不是可移植优化。
}

}  // namespace
