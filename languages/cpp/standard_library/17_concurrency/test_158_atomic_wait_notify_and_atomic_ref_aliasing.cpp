// polyglot-covers:
// - cpp.stdlib.concurrency.atomic-wait-value-change-loop-and-notify-one
// - cpp.stdlib.concurrency.atomic-notify-without-value-change-and-aba-trap
// - cpp.stdlib.concurrency.atomic-notify-all-multiple-waiters
// - cpp.stdlib.concurrency.atomic-flag-wait-notify-and-test
// - cpp.stdlib.concurrency.atomic-ref-aliases-existing-object-and-lifetime
// - cpp.stdlib.concurrency.atomic-ref-required-alignment-and-lock-free-query
// - cpp.stdlib.concurrency.atomic-ref-wait-notify-on-referenced-object
// - cpp.stdlib.concurrency.atomic-ref-integral-floating-and-pointer-operations
// - cpp.stdlib.concurrency.atomic-ref-concurrent-access-must-remain-atomic

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <cstddef>
#include <future>
#include <thread>
#include <type_traits>
#include <vector>

namespace {

TEST(AtomicWaiting, StoreThenNotifyOneUnblocksAWaiterWhenTheValueDiffers) {
  std::atomic<int> state{0};
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<int> observed;
  auto observed_future = observed.get_future();

  std::thread waiter{[&] {
    entered.set_value();
    state.wait(0, std::memory_order_acquire);
    observed.set_value(state.load(std::memory_order_relaxed));
  }};
  entered_future.wait();
  state.store(1, std::memory_order_release);
  state.notify_one();

  EXPECT_EQ(observed_future.get(), 1);
  waiter.join();

  // wait(old) 内部会反复比较值并只在值不同后返回；notify 本身不修改值。即使 store
  // 发生在 waiter 真正阻塞前，wait 初次比较也能发现变化，不存在丢通知问题。
}

TEST(AtomicWaiting, NotificationWithoutAValueChangeDoesNotSatisfyWait) {
  std::atomic<int> state{0};
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<void> returned;
  auto returned_future = returned.get_future();

  std::thread waiter{[&] {
    entered.set_value();
    state.wait(0);
    returned.set_value();
  }};
  entered_future.wait();
  state.notify_one();
  EXPECT_EQ(returned_future.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::timeout);

  state.store(2);
  state.notify_one();
  returned_future.wait();
  waiter.join();

  // 底层阻塞可以伪唤醒，但 atomic::wait 不会在值仍等于 old 时返回。比较的是值表示；
  // 若值从 A 变 B 又在观察前变回 A（ABA），wait 可能完全看不到中间变化。
}

TEST(AtomicWaiting, NotifyAllReleasesAllWaitersAfterOnePublishedChange) {
  std::atomic<int> generation{0};
  std::atomic<int> entered{0};
  std::vector<int> observations(3, 0);
  std::vector<std::thread> waiters;

  for (int index = 0; index < 3; ++index) {
    waiters.emplace_back([&, index] {
      entered.fetch_add(1, std::memory_order_release);
      generation.wait(0, std::memory_order_acquire);
      observations[static_cast<std::size_t>(index)] =
          generation.load(std::memory_order_relaxed);
    });
  }
  while (entered.load(std::memory_order_acquire) != 3) {
    std::this_thread::yield();
  }
  generation.store(1, std::memory_order_release);
  generation.notify_all();

  for (auto& waiter : waiters) {
    waiter.join();
  }
  EXPECT_EQ(observations, (std::vector<int>{1, 1, 1}));

  // notify_all 只唤醒当前阻塞者；后到的 wait 也会因值已变化而直接返回。
}

TEST(AtomicFlagWaiting, ClearAndNotifyPublishTheUnlockedState) {
  std::atomic_flag flag{};
  flag.test_and_set(std::memory_order_relaxed);
  int payload = 0;
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<int> observed;
  auto observed_future = observed.get_future();

  std::thread waiter{[&] {
    entered.set_value();
    flag.wait(true, std::memory_order_acquire);
    observed.set_value(payload);
  }};
  entered_future.wait();
  payload = 55;
  flag.clear(std::memory_order_release);
  flag.notify_one();

  EXPECT_EQ(observed_future.get(), 55);
  waiter.join();

  // atomic_flag 也有 C++20 wait/notify；release clear 与读到 false 的 acquire wait
  // 建立同步。仍须先改值再通知，通知不是独立保存的事件。
}

TEST(AtomicRef, OperationsDirectlyModifyTheReferencedObject) {
  alignas(std::atomic_ref<int>::required_alignment) int value = 3;
  std::atomic_ref<int> first{value};
  std::atomic_ref<int> second{value};

  EXPECT_EQ(first.fetch_add(4), 3);
  EXPECT_EQ(first.load(), 7);
  second.store(11);
  EXPECT_EQ(first.load(), 11);

  // atomic_ref 不拥有也不复制对象，多个引用同一对象的 atomic_ref 参与同一原子
  // 修改顺序。被引用对象必须活得更久，而且在引用存续期间不得被移动到别处。
}

TEST(AtomicRef, RequiredAlignmentAndLockFreeStatusBelongToTheReferencedType) {
  alignas(std::atomic_ref<int>::required_alignment) int value = 0;
  std::atomic_ref<int> reference{value};

  static_assert(std::atomic_ref<int>::required_alignment >= alignof(int));
  EXPECT_EQ(reference.is_lock_free(), std::atomic_ref<int>::is_always_lock_free);
  static_assert(std::is_trivially_copyable_v<decltype(reference)>);

  // 构造 atomic_ref 的对象地址必须满足 required_alignment，它可能严于 alignof(T)。
  // 该约束无法靠运行时补救，适配 packed/外部缓冲区时尤其容易踩坑。
}

TEST(AtomicRefSpecializations, IntegralFloatingAndPointerReferencesProvideFetchOps) {
  alignas(std::atomic_ref<unsigned>::required_alignment) unsigned bits = 1U;
  {
    std::atomic_ref<unsigned> bit_ref{bits};
    EXPECT_EQ(bit_ref.fetch_or(4U), 1U);
    EXPECT_EQ(bit_ref.load(), 5U);
  }
  EXPECT_EQ(bits, 5U);

  alignas(std::atomic_ref<double>::required_alignment) double number = 1.0;
  {
    std::atomic_ref<double> number_ref{number};
    EXPECT_DOUBLE_EQ(number_ref.fetch_add(0.5), 1.0);
    EXPECT_DOUBLE_EQ(number_ref.load(), 1.5);
  }
  EXPECT_DOUBLE_EQ(number, 1.5);

  int values[] = {1, 2, 3};
  alignas(std::atomic_ref<int*>::required_alignment) int* cursor = values;
  {
    std::atomic_ref<int*> pointer_ref{cursor};
    EXPECT_EQ(pointer_ref.fetch_add(2), values);
    EXPECT_EQ(pointer_ref.load(), values + 2);
  }
  EXPECT_EQ(cursor, values + 2);
}

TEST(AtomicRefWaiting, WaitAndNotifyOperateOnTheReferencedObjectsAtomicValue) {
  alignas(std::atomic_ref<int>::required_alignment) int state = 0;
  std::atomic_ref<int> reference{state};
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<int> observed;
  auto observed_future = observed.get_future();

  std::thread waiter{[reference, &entered, &observed] {
    entered.set_value();
    reference.wait(0, std::memory_order_acquire);
    observed.set_value(reference.load(std::memory_order_relaxed));
  }};
  entered_future.wait();
  reference.store(1, std::memory_order_release);
  reference.notify_all();

  EXPECT_EQ(observed_future.get(), 1);
  waiter.join();

  // atomic_ref 的 wait/notify 与 atomic<T> 相同，但阻塞键关联的是已有对象的地址；
  // 等待期间销毁引用或底层对象都会破坏生命周期前置条件。
}

TEST(AtomicRefLifetime, NonAtomicAccessMustNotOverlapAnyAtomicReferenceUse) {
  alignas(std::atomic_ref<int>::required_alignment) int value = 1;
  {
    std::atomic_ref<int> reference{value};
    reference.store(2, std::memory_order_relaxed);
    EXPECT_EQ(reference.load(std::memory_order_relaxed), 2);

    // reference 存续期间，所有访问都必须通过 atomic_ref；这比“只有并发时才原子”
    // 更严格。混用裸 int 读写会违反 atomic_ref 的使用前置条件。
  }
  value = 3;  // atomic_ref 生命周期结束且没有并发访问，可恢复普通访问。
  EXPECT_EQ(value, 3);
}

}  // namespace
