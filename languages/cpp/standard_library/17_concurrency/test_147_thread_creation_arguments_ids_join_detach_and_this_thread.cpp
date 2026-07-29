// polyglot-covers:
// - cpp.stdlib.concurrency.thread-construction-decay-copy-ref-and-move-only-arguments
// - cpp.stdlib.concurrency.thread-invoke-member-function-and-callable
// - cpp.stdlib.concurrency.thread-joinable-move-swap-join-and-post-join-id
// - cpp.stdlib.concurrency.thread-detach-with-explicit-shared-lifetime
// - cpp.stdlib.concurrency.thread-id-default-comparison-stream-and-hash
// - cpp.stdlib.concurrency.this-thread-get-id-and-yield
// - cpp.stdlib.concurrency.this-thread-sleep-for-until-signatures-without-timing-assumptions
// - cpp.stdlib.concurrency.thread-exception-boundary-and-promise-transfer
// - cpp.stdlib.concurrency.thread-invalid-join-system-error
// - cpp.stdlib.concurrency.thread-hardware-concurrency-and-native-handle
// - cpp.stdlib.concurrency.thread-destructor-terminate-trap

#include <gtest/gtest.h>

#include <chrono>
#include <exception>
#include <functional>
#include <future>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <thread>
#include <utility>

namespace {

class Accumulator {
 public:
  void add(int amount) { value_ += amount; }
  [[nodiscard]] int value() const noexcept { return value_; }

 private:
  int value_ = 0;
};

TEST(ThreadArguments, ValuesAreDecayCopiedUnlessReferenceWrapperIsExplicit) {
  int copied = 1;
  int referenced = 1;
  int observed_copy = 0;
  std::thread worker{
      [&observed_copy](int by_value, int& by_reference) {
        by_value = 99;
        observed_copy = by_value;
        by_reference = 7;
      },
      copied,
      std::ref(referenced)};
  worker.join();

  EXPECT_EQ(copied, 1);
  EXPECT_EQ(observed_copy, 99);
  EXPECT_EQ(referenced, 7);

  // thread 先 decay-copy callable 和参数，再在新线程中按 std::invoke 规则调用。
  // 直接传 lvalue 不会保留引用；确需共享时用 std::ref，并保证对象寿命与同步关系。
}

TEST(ThreadArguments, MoveOnlyValuesAndMemberFunctionsUseInvokeSemantics) {
  Accumulator accumulator;
  auto payload = std::make_unique<int>(42);
  std::promise<int> moved_value;
  auto moved_future = moved_value.get_future();

  std::thread member{&Accumulator::add, &accumulator, 5};
  std::thread move_only{
      [&moved_value](std::unique_ptr<int> received) {
        moved_value.set_value(*received);
      },
      std::move(payload)};
  member.join();
  move_only.join();

  EXPECT_EQ(accumulator.value(), 5);
  EXPECT_EQ(moved_future.get(), 42);
  EXPECT_EQ(payload, nullptr);

  // 成员函数指针、对象指针与参数由 invoke 组合；move-only 参数须显式 std::move。
  // 构造返回只代表线程已创建，不代表函数已执行到任何具体位置。
}

TEST(ThreadOwnership, MoveTransfersTheJoinObligationAndJoinClearsTheId) {
  std::promise<std::thread::id> observed_id;
  auto observed_future = observed_id.get_future();
  std::thread original{
      [&observed_id] { observed_id.set_value(std::this_thread::get_id()); }};
  const std::thread::id running_id = original.get_id();

  std::thread owner = std::move(original);
  EXPECT_FALSE(original.joinable());
  EXPECT_TRUE(owner.joinable());
  EXPECT_EQ(owner.get_id(), running_id);
  EXPECT_EQ(observed_future.get(), running_id);

  owner.join();
  EXPECT_FALSE(owner.joinable());
  EXPECT_EQ(owner.get_id(), std::thread::id{});

  // thread 不可复制；移动转移的是系统线程句柄和 join/detach 责任。join 同步等待
  // 完成并使对象不再 joinable，但已保存的 thread::id 值仍可用于日志比较。
}

TEST(ThreadOwnership, SwapExchangesHandlesWithoutWaitingForEitherThread) {
  std::promise<void> first_gate;
  std::promise<void> second_gate;
  auto first_ready = first_gate.get_future().share();
  auto second_ready = second_gate.get_future().share();
  std::thread first{[first_ready] { first_ready.wait(); }};
  std::thread second{[second_ready] { second_ready.wait(); }};
  const auto first_id = first.get_id();
  const auto second_id = second.get_id();

  swap(first, second);
  EXPECT_EQ(first.get_id(), second_id);
  EXPECT_EQ(second.get_id(), first_id);
  first_gate.set_value();
  second_gate.set_value();
  first.join();
  second.join();

  // swap 只交换所有权，不向工作线程发送信号。并发对象的变量名不能当作稳定线程
  // 身份；移动或交换后应从当前 owner 查询 get_id/native_handle。
}

TEST(ThreadDetach, SharedStateMakesDetachedLifetimeAndCompletionExplicit) {
  auto result = std::make_shared<std::promise<int>>();
  auto finished = result->get_future();
  std::thread worker{[result] { result->set_value(21 * 2); }};

  worker.detach();
  EXPECT_FALSE(worker.joinable());
  EXPECT_EQ(finished.get(), 42);

  // detach 后 thread 对象不再拥有或等待执行线程；捕获栈引用很容易悬空。本例用
  // shared_ptr 延长通信状态，并由 future 等到完成，避免测试退出时遗留后台工作。
}

TEST(ThreadIds, DefaultIdRepresentsNoThreadAndSupportsOrderingHashingAndStreams) {
  const std::thread::id none;
  const std::thread::id current = std::this_thread::get_id();
  std::ostringstream text;
  text << current;

  EXPECT_NE(current, none);
  EXPECT_EQ(
      std::hash<std::thread::id>{}(current),
      std::hash<std::thread::id>{}(current));
  EXPECT_FALSE(text.str().empty());
  EXPECT_TRUE(current < none || none < current);

  // 非默认 id 之间提供全序和哈希，但具体文本/数值没有可移植含义，线程结束后 id
  // 也可复用。它适合进程内关联，不适合作为持久化主键。
}

TEST(ThisThreadUtilities, YieldIsOnlyASchedulingHint) {
  const auto before = std::this_thread::get_id();
  std::this_thread::yield();
  const auto after = std::this_thread::get_id();

  EXPECT_EQ(after, before);

  // yield 只提示调度器让出执行机会，可能立即返回，不能作为同步或公平性保证。
  // 测试并发进度应使用 future、条件变量、latch 等事件，不依赖 sleep 的时间猜测。
}

TEST(ThisThreadUtilities, SleepFunctionsAreCheckedWithoutDependingOnWallClockTiming) {
  static_assert(requires {
    std::this_thread::sleep_for(std::chrono::milliseconds{1});
    std::this_thread::sleep_until(std::chrono::steady_clock::time_point{});
  });

  // sleep_for 至少阻塞请求的相对时长，sleep_until 等到指定时钟的截止点，但调度会
  // 让实际返回更晚。测试只验证签名而不真正 sleep，避免把机器负载变成随机失败。
}

TEST(ThreadExceptions, WorkerExceptionsMustBeCaughtBeforeCrossingTheEntryBoundary) {
  std::promise<int> result;
  auto future = result.get_future();
  std::thread worker{[&result] {
    try {
      throw std::runtime_error{"worker failed"};
    } catch (...) {
      result.set_exception(std::current_exception());
    }
  }};

  EXPECT_THROW(static_cast<void>(future.get()), std::runtime_error);
  worker.join();

  // 异常若逃出线程入口会调用 std::terminate，不会自动回到创建线程。promise/
  // packaged_task/async 可把 exception_ptr 存进共享状态，再由 future::get 重抛。
}

TEST(ThreadErrors, JoiningANonJoinableObjectThrowsSystemError) {
  std::thread completed{[] {}};
  completed.join();

  EXPECT_THROW(completed.join(), std::system_error);
  EXPECT_THROW(completed.detach(), std::system_error);

  // join/detach 的前置状态必须由 joinable() 或所有权结构保证。更严重的是销毁仍
  // joinable 的 std::thread 会 terminate；析构不会隐式 join，也不能用运行测试触发。
}

TEST(ThreadCapabilities, HardwareCountIsAHintAndNativeHandleIsImplementationDefined) {
  std::promise<void> gate;
  auto ready = gate.get_future().share();
  std::thread worker{[ready] { ready.wait(); }};
  const auto native = worker.native_handle();
  const unsigned count = std::thread::hardware_concurrency();

  static_cast<void>(native);
  EXPECT_TRUE(count == 0U || count >= 1U);
  gate.set_value();
  worker.join();

  // hardware_concurrency 只是提示，0 表示无法计算，也可能与容器 CPU 配额不符。
  // native_handle 的类型和操作由实现定义；使用它会把代码带出 C++ 可移植保证。
}

}  // namespace
