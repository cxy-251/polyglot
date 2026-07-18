// polyglot-covers:
// - cpp.stdlib.concurrency.once-flag-single-successful-invocation
// - cpp.stdlib.concurrency.call-once-perfect-forwarding-and-invoke-semantics
// - cpp.stdlib.concurrency.call-once-exception-retry-and-active-call-order
// - cpp.stdlib.concurrency.call-once-return-synchronizes-passive-calls
// - cpp.stdlib.concurrency.once-flag-noncopyable-lifetime-and-reentrancy-trap

#include <gtest/gtest.h>

#include <atomic>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(CallOnce, ConcurrentCallersRunExactlyOneSuccessfulInvocation) {
  std::once_flag flag;
  std::atomic<int> attempts{0};
  int published_value = 0;
  std::promise<void> start;
  auto start_future = start.get_future().share();
  std::vector<int> observations(4, 0);
  std::vector<std::thread> callers;

  for (int index = 0; index < 4; ++index) {
    callers.emplace_back([&, index] {
      start_future.wait();
      std::call_once(flag, [&] {
        attempts.fetch_add(1, std::memory_order_relaxed);
        published_value = 73;
      });
      observations[static_cast<std::size_t>(index)] = published_value;
    });
  }
  start.set_value();
  for (auto& caller : callers) {
    caller.join();
  }

  EXPECT_EQ(attempts.load(std::memory_order_relaxed), 1);
  EXPECT_EQ(observations, (std::vector<int>{73, 73, 73, 73}));

  // 成功的 returning call 只发生一次，其返回同步于所有 passive call 的返回；
  // 因而调用者无需另加原子变量，也能看到初始化中写入的普通对象。
}

struct Receiver {
  void Store(std::unique_ptr<int> value) {
    stored = *value;
  }

  int stored = 0;
};

TEST(CallOnce, ArgumentsUseInvokeAndArePerfectForwardedOnlyByTheActiveCall) {
  std::once_flag flag;
  Receiver receiver;

  std::call_once(
      flag, &Receiver::Store, std::ref(receiver), std::make_unique<int>(42));
  std::call_once(
      flag, &Receiver::Store, std::ref(receiver), std::make_unique<int>(99));

  EXPECT_EQ(receiver.stored, 42);

  // call_once 像 std::invoke 一样支持成员函数和 reference_wrapper，并把参数完美
  // 转发给真正成为 active 的调用。第二次调用是 passive，函数体不会执行。
}

TEST(CallOnce, ThrowingActiveCallsLeaveTheFlagAvailableForRetry) {
  std::once_flag flag;
  int attempts = 0;
  auto initialize = [&] {
    ++attempts;
    if (attempts < 3) {
      throw std::runtime_error{"not ready"};
    }
  };

  EXPECT_THROW(std::call_once(flag, initialize), std::runtime_error);
  EXPECT_THROW(std::call_once(flag, initialize), std::runtime_error);
  EXPECT_NO_THROW(std::call_once(flag, initialize));
  EXPECT_NO_THROW(std::call_once(flag, initialize));
  EXPECT_EQ(attempts, 3);

  // 抛异常的 active call 是 exceptional，不会把 once_flag 标记为完成。所有 active
  // call 形成一个总序；前一个 exceptional 返回同步于下一个 active 的开始。
}

TEST(CallOnce, OneConcurrentExceptionIsObservedOnlyByItsActiveCaller) {
  std::once_flag flag;
  std::atomic<int> attempts{0};
  std::atomic<int> exceptions{0};
  int value = 0;
  std::promise<void> start;
  auto start_future = start.get_future().share();
  std::vector<std::thread> callers;

  for (int index = 0; index < 3; ++index) {
    callers.emplace_back([&] {
      start_future.wait();
      try {
        std::call_once(flag, [&] {
          const int number = attempts.fetch_add(1, std::memory_order_relaxed);
          if (number == 0) {
            throw std::runtime_error{"first attempt"};
          }
          value = 81;
        });
      } catch (const std::runtime_error&) {
        exceptions.fetch_add(1, std::memory_order_relaxed);
      }
    });
  }
  start.set_value();
  for (auto& caller : callers) {
    caller.join();
  }

  EXPECT_EQ(attempts.load(std::memory_order_relaxed), 2);
  EXPECT_EQ(exceptions.load(std::memory_order_relaxed), 1);
  EXPECT_EQ(value, 81);

  // exceptional call 的异常只传给执行它的调用者；其他并发调用不会共同失败，
  // 而是由其中一个重试，成功后其余调用转为 passive。
}

TEST(OnceFlagProperties, FlagIsAnOpaqueNoncopyableLifetimeBoundState) {
  static_assert(std::is_default_constructible_v<std::once_flag>);
  static_assert(!std::is_copy_constructible_v<std::once_flag>);
  static_assert(!std::is_copy_assignable_v<std::once_flag>);
  static_assert(!std::is_move_constructible_v<std::once_flag>);

  std::once_flag flag;
  int calls = 0;
  std::call_once(flag, [&] { ++calls; });
  std::call_once(flag, [&] { ++calls; });
  EXPECT_EQ(calls, 1);

  // flag 没有 reset；要重新初始化只能建立新对象，并保证旧 flag 与所有 call_once
  // 都已结束。初始化函数若用同一个 flag 递归调用 call_once，通常会自我死锁。
}

}  // namespace
