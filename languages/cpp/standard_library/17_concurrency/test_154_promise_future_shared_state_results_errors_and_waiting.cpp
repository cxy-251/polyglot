// polyglot-covers:
// - cpp.stdlib.concurrency.promise-future-shared-state-value-and-consumption
// - cpp.stdlib.concurrency.promise-reference-and-void-specializations
// - cpp.stdlib.concurrency.promise-exception-and-future-rethrow
// - cpp.stdlib.concurrency.promise-broken-state-and-future-error-codes
// - cpp.stdlib.concurrency.promise-get-future-and-satisfaction-preconditions
// - cpp.stdlib.concurrency.promise-set-value-at-thread-exit-readiness
// - cpp.stdlib.concurrency.promise-set-exception-at-thread-exit-readiness
// - cpp.stdlib.concurrency.future-wait-wait-for-wait-until-and-valid
// - cpp.stdlib.concurrency.promise-move-swap-and-allocator-awareness
// - cpp.stdlib.concurrency.future-error-category-codes-and-error-code-integration

#include <gtest/gtest.h>

#include <chrono>
#include <exception>
#include <future>
#include <memory>
#include <stdexcept>
#include <string>
#include <system_error>
#include <thread>
#include <type_traits>
#include <utility>

namespace {

TEST(PromiseFuture, ValueMakesTheSharedStateReadyAndGetConsumesTheFuture) {
  std::promise<std::string> producer;
  std::future<std::string> consumer = producer.get_future();

  EXPECT_TRUE(consumer.valid());
  producer.set_value("ready");
  EXPECT_EQ(consumer.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::ready);
  EXPECT_EQ(consumer.get(), "ready");
  EXPECT_FALSE(consumer.valid());

  // promise 和 future 是同一个 shared state 的生产者/唯一消费者句柄。get 移出结果
  // 后释放 shared state，并使 future 无效；再次 wait/get 会抛 no_state。
  EXPECT_THROW(static_cast<void>(consumer.get()), std::future_error);
}

TEST(PromiseSpecializations, ReferenceResultAliasesTheOriginalObject) {
  int value = 7;
  std::promise<int&> producer;
  auto consumer = producer.get_future();
  producer.set_value(value);

  int& result = consumer.get();
  EXPECT_EQ(&result, &value);
  result = 19;
  EXPECT_EQ(value, 19);

  // promise<T&> 保存引用而不是复制对象；生产者必须保证被引用对象活到 consumer
  // 取用结束。普通 promise<T> 的 set_value 则把值复制或移动进 shared state。
}

TEST(PromiseSpecializations, VoidStateRepresentsCompletionWithoutAPayload) {
  std::promise<void> producer;
  auto consumer = producer.get_future();
  producer.set_value();

  EXPECT_NO_THROW(consumer.get());
  EXPECT_FALSE(consumer.valid());

  // promise<void> 仍携带 ready 状态和异常通道，只是成功结果没有值。
}

TEST(PromiseFuture, StoredExceptionIsRethrownByGetInTheConsumer) {
  std::promise<int> producer;
  auto consumer = producer.get_future();
  producer.set_exception(
      std::make_exception_ptr(std::runtime_error{"worker failed"}));

  try {
    static_cast<void>(consumer.get());
    FAIL() << "future::get should rethrow the stored exception";
  } catch (const std::runtime_error& error) {
    EXPECT_STREQ(error.what(), "worker failed");
  }
  EXPECT_FALSE(consumer.valid());

  // 异常对象通过 exception_ptr 存进 shared state；wait 只等待 ready，不抛该异常，
  // 真正的重抛发生在 get。不要忘记 get，否则后台失败可能被静默忽略。
}

TEST(PromiseFutureErrors, AbandonedProducerStoresBrokenPromise) {
  std::future<int> consumer;
  {
    std::promise<int> producer;
    consumer = producer.get_future();
  }

  try {
    static_cast<void>(consumer.get());
    FAIL() << "an abandoned promise should break the shared state";
  } catch (const std::future_error& error) {
    EXPECT_EQ(error.code(), std::make_error_code(std::future_errc::broken_promise));
  }

  // 最后一个 producer 未提供结果就释放 shared state 时，库写入 broken_promise，
  // 让 consumer 不会永久等待。没有相应 future 的临时 promise 析构则无需报告。
}

TEST(PromiseFutureErrors, RetrievalAndSatisfactionAreEachAllowedOnlyOnce) {
  std::promise<int> producer;
  auto consumer = producer.get_future();

  try {
    static_cast<void>(producer.get_future());
    FAIL() << "get_future should be single-shot";
  } catch (const std::future_error& error) {
    EXPECT_EQ(error.code(),
              std::make_error_code(std::future_errc::future_already_retrieved));
  }

  producer.set_value(4);
  try {
    producer.set_value(5);
    FAIL() << "a shared state cannot be satisfied twice";
  } catch (const std::future_error& error) {
    EXPECT_EQ(error.code(),
              std::make_error_code(std::future_errc::promise_already_satisfied));
  }
  EXPECT_EQ(consumer.get(), 4);
}

TEST(PromiseFutureErrors, FutureErrcIntegratesWithTheSystemErrorModel) {
  static_assert(std::is_error_code_enum_v<std::future_errc>);
  const std::error_code error = std::future_errc::no_state;

  EXPECT_EQ(error, std::make_error_code(std::future_errc::no_state));
  EXPECT_EQ(&error.category(), &std::future_category());
  EXPECT_FALSE(error.message().empty());

  // future_errc 可隐式构造 error_code，并使用 future_category；错误文本由实现决定，
  // 稳定判断应比较枚举/错误码，而不是解析 message。
}

TEST(PromiseAtThreadExit, StateBecomesReadyOnlyWhenTheProducerThreadExits) {
  std::promise<int> producer;
  auto consumer = producer.get_future();
  std::promise<void> registered;
  auto registered_future = registered.get_future();
  std::promise<void> may_exit;
  auto may_exit_future = may_exit.get_future().share();

  std::thread worker{[producer = std::move(producer), &registered,
                      may_exit_future]() mutable {
    producer.set_value_at_thread_exit(88);
    registered.set_value();
    may_exit_future.wait();
  }};
  registered_future.wait();
  EXPECT_EQ(consumer.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::timeout);

  may_exit.set_value();
  worker.join();
  EXPECT_EQ(consumer.get(), 88);

  // set_value_at_thread_exit 先存结果，却把 ready 推迟到线程局部对象销毁之后；
  // 适合“线程真正结束”才算完成的协议，而不是普通任务一算完就发布结果。
}

TEST(PromiseAtThreadExit, StoredExceptionIsAlsoPublishedOnlyAtThreadExit) {
  std::promise<int> producer;
  auto consumer = producer.get_future();
  std::promise<void> registered;
  auto registered_future = registered.get_future();
  std::promise<void> may_exit;
  auto may_exit_future = may_exit.get_future().share();

  std::thread worker{[producer = std::move(producer), &registered,
                      may_exit_future]() mutable {
    producer.set_exception_at_thread_exit(
        std::make_exception_ptr(std::logic_error{"late failure"}));
    registered.set_value();
    may_exit_future.wait();
  }};
  registered_future.wait();
  EXPECT_EQ(consumer.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::timeout);

  may_exit.set_value();
  worker.join();
  EXPECT_THROW(static_cast<void>(consumer.get()), std::logic_error);

  // 异常版本同样先保存 exception_ptr、在线程退出时才标记 ready；不能与 set_value
  // 或其他满足操作混用，否则 promise_already_satisfied。
}

TEST(FutureWaiting, TimedWaitReportsTimeoutThenReadyWithoutConsumingTheValue) {
  std::promise<int> producer;
  auto consumer = producer.get_future();

  EXPECT_EQ(consumer.wait_for(std::chrono::milliseconds::zero()),
            std::future_status::timeout);
  EXPECT_EQ(consumer.wait_until(std::chrono::steady_clock::now()),
            std::future_status::timeout);
  EXPECT_TRUE(consumer.valid());

  producer.set_value(12);
  consumer.wait();
  EXPECT_TRUE(consumer.valid());
  EXPECT_EQ(consumer.get(), 12);

  // wait/wait_for/wait_until 都不消费结果；定时等待还可能比 deadline 晚返回，
  // 业务逻辑应依据 future_status，而不是测量实际经过了多少墙钟时间。
}

TEST(PromiseOwnership, MoveAndSwapTransferProducerHandlesNotTheResultValue) {
  static_assert(std::uses_allocator_v<std::promise<int>, std::allocator<int>>);
  static_assert(!std::is_copy_constructible_v<std::promise<int>>);

  std::promise<int> first;
  std::promise<int> second;
  auto first_future = first.get_future();
  auto second_future = second.get_future();

  swap(first, second);
  second.set_value(1);
  first.set_value(2);
  EXPECT_EQ(first_future.get(), 1);
  EXPECT_EQ(second_future.get(), 2);

  std::promise<int> source;
  auto moved_future = source.get_future();
  std::promise<int> destination = std::move(source);
  destination.set_value(3);
  EXPECT_EQ(moved_future.get(), 3);
  EXPECT_THROW(source.set_value(4), std::future_error);

  std::promise<int> allocated{
      std::allocator_arg, std::allocator<int>{}};
  auto allocated_future = allocated.get_future();
  allocated.set_value(5);
  EXPECT_EQ(allocated_future.get(), 5);

  // move/swap 迁移的是 producer 与 shared state 的关联；移后 promise 没有状态。
  // uses_allocator 支持只控制 shared state 的内部配置，不改变结果对象的 allocator。
}

}  // namespace
