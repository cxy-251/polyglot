// polyglot-covers:
// - cpp.stdlib.concurrency.async-launch-async-thread-and-exception-capture
// - cpp.stdlib.concurrency.async-launch-deferred-lazy-invocation-and-status
// - cpp.stdlib.concurrency.async-default-policy-unspecified-selection
// - cpp.stdlib.concurrency.async-decay-copy-invoke-and-move-only-arguments
// - cpp.stdlib.concurrency.async-future-temporary-destructor-waits
// - cpp.stdlib.concurrency.future-share-invalidates-unique-future
// - cpp.stdlib.concurrency.shared-future-copy-multiple-get-reference-and-exception

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <functional>
#include <future>
#include <memory>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

TEST(AsyncPolicies, AsyncPolicyRunsOnADistinctThreadAndCapturesExceptions) {
  const auto caller = std::this_thread::get_id();
  auto id_future = std::async(std::launch::async, [] {
    return std::this_thread::get_id();
  });
  EXPECT_NE(id_future.get(), caller);

  auto error_future = std::async(std::launch::async, []() -> int {
    throw std::runtime_error{"async failure"};
  });
  EXPECT_THROW(static_cast<void>(error_future.get()), std::runtime_error);

  // launch::async 要求像新线程一样异步执行；函数返回或抛出的异常都存入 shared
  // state，调用 std::async 本身不会把任务异常直接抛给调用者。
}

TEST(AsyncPolicies, DeferredPolicyRunsLazilyOnTheWaitingThread) {
  const auto caller = std::this_thread::get_id();
  std::atomic<bool> invoked{false};
  auto future = std::async(std::launch::deferred, [&] {
    invoked.store(true, std::memory_order_relaxed);
    return std::this_thread::get_id();
  });

  EXPECT_FALSE(invoked.load(std::memory_order_relaxed));
  EXPECT_EQ(future.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::deferred);
  EXPECT_EQ(future.get(), caller);
  EXPECT_TRUE(invoked.load(std::memory_order_relaxed));

  // deferred 函数在第一次非定时 wait/get 的线程中惰性执行；只有 timed wait 不会
  // 触发它，而是返回 deferred。若 future 从未被等待，函数可以永远不运行。
}

TEST(AsyncPolicies, DefaultPolicyMayChooseAsyncOrDeferred) {
  auto future = std::async([] { return 6 * 7; });
  const auto status = future.wait_for(std::chrono::milliseconds::zero());

  EXPECT_TRUE(status == std::future_status::deferred ||
              status == std::future_status::timeout ||
              status == std::future_status::ready);
  EXPECT_EQ(future.get(), 42);

  // 未显式给 policy 等价于 async|deferred，具体选择由实现决定；不能假设一定并发，
  // 也不能用一次 status 结果推断其他运行的选择。需要并发时应写 launch::async。
}

struct AsyncReceiver {
  int Add(std::unique_ptr<int> amount) {
    value += *amount;
    return value;
  }

  int value = 1;
};

TEST(AsyncArguments, InvocationSupportsReferencesMembersAndMoveOnlyValues) {
  AsyncReceiver receiver;
  auto future = std::async(
      std::launch::deferred, &AsyncReceiver::Add, std::ref(receiver),
      std::make_unique<int>(4));

  EXPECT_EQ(future.get(), 5);
  EXPECT_EQ(receiver.value, 5);

  // 函数与参数在 async 返回前按 decay-copy 保存，真正调用使用 std::invoke 语义；
  // std::ref 才保留引用，unique_ptr 则被移动进任务。裸引用捕获还要保证异步寿命。
}

TEST(AsyncLifetime, DestroyingTheLastAsyncFutureWaitsForTheTask) {
  std::promise<void> task_started;
  auto task_started_future = task_started.get_future();
  std::promise<void> release_task;
  auto release_task_future = release_task.get_future().share();
  auto future = std::async(std::launch::async, [&] {
    task_started.set_value();
    release_task_future.wait();
  });
  task_started_future.wait();

  std::promise<void> destruction_started;
  auto destruction_started_future = destruction_started.get_future();
  std::promise<void> destruction_finished;
  auto destruction_finished_future = destruction_finished.get_future();
  std::thread destroyer{[future = std::move(future), &destruction_started,
                         &destruction_finished]() mutable {
    destruction_started.set_value();
    future = std::future<void>{};
    destruction_finished.set_value();
  }};
  destruction_started_future.wait();
  EXPECT_EQ(destruction_finished_future.wait_for(
                std::chrono::milliseconds::zero()),
            std::future_status::timeout);

  release_task.set_value();
  destruction_finished_future.wait();
  destroyer.join();

  // 由 launch::async 创建的 shared state，在最后一个引用它的 future 析构/替换时
  // 可能等待任务完成。这会让看似被丢弃的临时 future 把两条语句意外串行化。
}

TEST(SharedFuture, ShareTransfersTheStateAndAllowsRepeatedConstGet) {
  std::promise<std::string> producer;
  std::future<std::string> unique = producer.get_future();
  std::shared_future<std::string> shared = unique.share();

  EXPECT_FALSE(unique.valid());
  EXPECT_TRUE(shared.valid());
  auto copied = shared;
  producer.set_value("many readers");

  const std::string& first = shared.get();
  const std::string& second = copied.get();
  EXPECT_EQ(first, "many readers");
  EXPECT_EQ(&first, &second);
  EXPECT_TRUE(shared.valid());
  EXPECT_TRUE(copied.valid());

  // share 把 unique future 变成无效并返回可复制句柄。shared_future<T>::get 返回
  // const T& 且可重复调用；引用只在至少一个 shared state 句柄存活时有效。
}

TEST(SharedFuture, CopiesCanSynchronizeManyConsumersButNotMutablePayloadAccess) {
  std::promise<int> producer;
  std::shared_future<int> shared = producer.get_future().share();
  std::vector<int> results(3, 0);
  std::vector<std::thread> consumers;

  for (int index = 0; index < 3; ++index) {
    consumers.emplace_back([copy = shared, &results, index] {
      results[static_cast<std::size_t>(index)] = copy.get();
    });
  }
  producer.set_value(27);
  for (auto& consumer : consumers) {
    consumer.join();
  }
  EXPECT_EQ(results, (std::vector<int>{27, 27, 27}));

  // 多线程在各自 shared_future 副本上等待/get 是安全的；若结果本身是引用或含
  // 可变共享状态，future 不会替 payload 提供数据竞争保护。
}

TEST(SharedFuture, ReferenceVoidAndExceptionStatesPreserveTheirSemantics) {
  int value = 9;
  std::promise<int&> reference_producer;
  auto reference = reference_producer.get_future().share();
  reference_producer.set_value(value);
  EXPECT_EQ(&reference.get(), &value);

  std::promise<void> void_producer;
  auto completion = void_producer.get_future().share();
  void_producer.set_value();
  EXPECT_NO_THROW(completion.get());
  EXPECT_NO_THROW(completion.get());

  std::promise<int> error_producer;
  auto error = error_producer.get_future().share();
  error_producer.set_exception(
      std::make_exception_ptr(std::logic_error{"shared error"}));
  EXPECT_THROW(static_cast<void>(error.get()), std::logic_error);
  EXPECT_THROW(static_cast<void>(error.get()), std::logic_error);
}

}  // namespace
