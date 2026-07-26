// polyglot-covers:
// - cpp.stdlib.concurrency.packaged-task-callable-shared-state-and-result
// - cpp.stdlib.concurrency.packaged-task-exception-capture
// - cpp.stdlib.concurrency.packaged-task-get-future-and-single-invocation-state
// - cpp.stdlib.concurrency.packaged-task-reset-and-old-shared-state
// - cpp.stdlib.concurrency.packaged-task-make-ready-at-thread-exit
// - cpp.stdlib.concurrency.packaged-task-move-swap-deduction-and-broken-promise

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <utility>

namespace {

TEST(PackagedTask, CallingTheWrapperStoresAResultForItsFuture) {
  std::packaged_task<int(int, int)> task{
      [](int left, int right) { return left + right; }};
  auto result = task.get_future();

  EXPECT_TRUE(task.valid());
  task(20, 22);
  EXPECT_EQ(result.get(), 42);

  // packaged_task 把 callable 和 promise-like shared state 绑在一起；operator()
  // 执行 callable 并发布结果，但它自身不返回该结果，consumer 从 future 获取。
}

TEST(PackagedTask, CallableExceptionsAreCapturedRatherThanEscapingOperatorCall) {
  std::packaged_task<int()> task{[]() -> int {
    throw std::runtime_error{"task failure"};
  }};
  auto result = task.get_future();

  EXPECT_NO_THROW(task());
  EXPECT_THROW(static_cast<void>(result.get()), std::runtime_error);

  // operator() 捕获 callable 的异常并把 exception_ptr 存入 shared state；只有
  // 包装器自身的状态错误（如已调用）才从 operator() 抛 future_error。
}

TEST(PackagedTaskErrors, FutureRetrievalAndStateSatisfactionAreSingleShot) {
  std::packaged_task<int()> task{[] { return 7; }};
  auto result = task.get_future();
  EXPECT_THROW(static_cast<void>(task.get_future()), std::future_error);

  task();
  EXPECT_THROW(task(), std::future_error);
  EXPECT_EQ(result.get(), 7);

  std::packaged_task<int()> empty;
  EXPECT_FALSE(empty.valid());
  EXPECT_THROW(empty(), std::future_error);
  EXPECT_THROW(static_cast<void>(empty.get_future()), std::future_error);
}

TEST(PackagedTask, ResetCreatesANewStateWhileKeepingTheCallable) {
  int calls = 0;
  std::packaged_task<int()> task{[&] { return ++calls; }};
  auto first = task.get_future();
  task();
  EXPECT_EQ(first.get(), 1);

  task.reset();
  auto second = task.get_future();
  task();
  EXPECT_EQ(second.get(), 2);

  // reset 丢弃旧 shared state、建立新状态，但保留 callable 及其内部状态。若旧状态
  // 尚未 ready，对应 future 会得到 broken_promise；reset 不是“清空 callable”。
}

TEST(PackagedTask, ResetBreaksAnUnfulfilledOldFuture) {
  std::packaged_task<int()> task{[] { return 1; }};
  auto abandoned = task.get_future();
  task.reset();

  try {
    static_cast<void>(abandoned.get());
    FAIL() << "reset should abandon the previous state";
  } catch (const std::future_error& error) {
    EXPECT_EQ(error.code(), std::make_error_code(std::future_errc::broken_promise));
  }

  auto current = task.get_future();
  task();
  EXPECT_EQ(current.get(), 1);
}

TEST(PackagedTaskAtThreadExit, InvocationStoresResultButDefersReadySignal) {
  std::packaged_task<int()> task{[] { return 64; }};
  auto result = task.get_future();
  std::promise<void> invoked;
  auto invoked_future = invoked.get_future();
  std::promise<void> may_exit;
  auto may_exit_future = may_exit.get_future().share();

  std::thread worker{[task = std::move(task), &invoked,
                      may_exit_future]() mutable {
    task.make_ready_at_thread_exit();
    invoked.set_value();
    may_exit_future.wait();
  }};
  invoked_future.wait();
  EXPECT_EQ(result.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::timeout);

  may_exit.set_value();
  worker.join();
  EXPECT_EQ(result.get(), 64);

  // make_ready_at_thread_exit 立即调用 callable 并存储结果，但像 promise 的对应接口
  // 一样延后 ready 通知。它也只允许满足当前 shared state 一次。
}

int Triple(int value) {
  return value * 3;
}

TEST(PackagedTaskOwnership, MoveSwapAndDeductionTransferTheTaskState) {
  std::packaged_task first{&Triple};
  static_assert(std::is_same_v<decltype(first), std::packaged_task<int(int)>>);
  auto first_result = first.get_future();

  std::packaged_task<int(int)> moved = std::move(first);
  EXPECT_FALSE(first.valid());
  EXPECT_TRUE(moved.valid());
  moved(4);
  EXPECT_EQ(first_result.get(), 12);

  std::packaged_task<int()> left{[] { return 1; }};
  std::packaged_task<int()> right{[] { return 2; }};
  auto left_result = left.get_future();
  auto right_result = right.get_future();
  swap(left, right);
  right();
  left();
  EXPECT_EQ(left_result.get(), 1);
  EXPECT_EQ(right_result.get(), 2);

  // move/swap 一并迁移 callable、shared state 和 get_future 是否已调用的状态。
  // packaged_task 是 move-only 类型，适合放进按移动语义传递的任务队列。
}

TEST(PackagedTaskLifetime, DestroyingAnUncalledTaskBreaksItsFuture) {
  std::future<int> result;
  {
    std::packaged_task<int()> task{[] { return 5; }};
    result = task.get_future();
  }

  try {
    static_cast<void>(result.get());
    FAIL() << "an abandoned task should break its state";
  } catch (const std::future_error& error) {
    EXPECT_EQ(error.code(), std::make_error_code(std::future_errc::broken_promise));
  }

  // packaged_task 不会因析构而自动执行 callable；未调用便析构时与 abandoned
  // promise 相同，consumer 收到 broken_promise，而不是默认构造的返回值。
}

}  // namespace
