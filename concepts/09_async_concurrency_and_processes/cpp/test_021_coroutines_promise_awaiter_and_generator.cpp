// polyglot-covers:
// - cpp.language.coroutine-promise-type
// - cpp.language.initial-and-final-suspend
// - cpp.language.co-yield-and-generator-laziness
// - cpp.language.co-await-awaiter-protocol
// - cpp.language.coroutine-frame-lifetime
// - cpp.language.coroutine-exception-propagation

#include <gtest/gtest.h>

#include <coroutine>
#include <exception>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

class IntGenerator {
 public:
  struct promise_type;
  using Handle = std::coroutine_handle<promise_type>;

  struct promise_type {
    int current_value{0};
    std::exception_ptr failure;

    IntGenerator get_return_object() { return IntGenerator{Handle::from_promise(*this)}; }
    std::suspend_always initial_suspend() const noexcept { return {}; }
    std::suspend_always final_suspend() const noexcept { return {}; }

    std::suspend_always yield_value(int value) noexcept {
      current_value = value;
      return {};
    }

    void return_void() const noexcept {}
    void unhandled_exception() noexcept { failure = std::current_exception(); }
  };

  class Iterator {
   public:
    explicit Iterator(Handle coroutine) : coroutine_(coroutine) {}

    int operator*() const { return coroutine_.promise().current_value; }

    Iterator& operator++() {
      coroutine_.resume();
      rethrow_if_finished_with_error();
      return *this;
    }

    bool operator==(std::default_sentinel_t) const {
      return !coroutine_ || coroutine_.done();
    }

   private:
    void rethrow_if_finished_with_error() const {
      if (coroutine_.done() && coroutine_.promise().failure) {
        std::rethrow_exception(coroutine_.promise().failure);
      }
    }

    Handle coroutine_;
  };

  IntGenerator(const IntGenerator&) = delete;
  IntGenerator& operator=(const IntGenerator&) = delete;

  IntGenerator(IntGenerator&& other) noexcept : coroutine_(std::exchange(other.coroutine_, {})) {}

  IntGenerator& operator=(IntGenerator&& other) noexcept {
    if (this != &other) {
      if (coroutine_) {
        coroutine_.destroy();
      }
      coroutine_ = std::exchange(other.coroutine_, {});
    }
    return *this;
  }

  ~IntGenerator() {
    if (coroutine_) {
      coroutine_.destroy();
    }
  }

  Iterator begin() {
    if (coroutine_) {
      coroutine_.resume();
      if (coroutine_.done() && coroutine_.promise().failure) {
        std::rethrow_exception(coroutine_.promise().failure);
      }
    }
    return Iterator{coroutine_};
  }

  std::default_sentinel_t end() const noexcept { return {}; }

 private:
  explicit IntGenerator(Handle coroutine) : coroutine_(coroutine) {}
  Handle coroutine_{};
};

IntGenerator counting_sequence(std::vector<std::string>& events, int count) {
  events.push_back("body started");
  for (int value = 1; value <= count; ++value) {
    co_yield value;
    events.push_back("resumed after " + std::to_string(value));
  }
  events.push_back("body completed");
}

class FrameProbe {
 public:
  explicit FrameProbe(std::vector<std::string>& events) : events_(events) {
    events_.push_back("frame resource acquired");
  }

  ~FrameProbe() { events_.push_back("frame resource released"); }

 private:
  std::vector<std::string>& events_;
};

IntGenerator suspended_resource(std::vector<std::string>& events) {
  FrameProbe probe{events};
  co_yield 7;
  co_yield 11;
}

IntGenerator failing_sequence() {
  co_yield 3;
  throw std::runtime_error{"coroutine failure"};
}

class IntTask {
 public:
  struct promise_type;
  using Handle = std::coroutine_handle<promise_type>;

  struct promise_type {
    int result{0};
    std::exception_ptr failure;

    IntTask get_return_object() { return IntTask{Handle::from_promise(*this)}; }
    std::suspend_never initial_suspend() const noexcept { return {}; }
    std::suspend_always final_suspend() const noexcept { return {}; }
    void return_value(int value) noexcept { result = value; }
    void unhandled_exception() noexcept { failure = std::current_exception(); }
  };

  IntTask(const IntTask&) = delete;
  IntTask& operator=(const IntTask&) = delete;
  IntTask(IntTask&& other) noexcept : coroutine_(std::exchange(other.coroutine_, {})) {}

  ~IntTask() {
    if (coroutine_) {
      coroutine_.destroy();
    }
  }

  int result() const {
    if (coroutine_.promise().failure) {
      std::rethrow_exception(coroutine_.promise().failure);
    }
    return coroutine_.promise().result;
  }

 private:
  explicit IntTask(Handle coroutine) : coroutine_(coroutine) {}
  Handle coroutine_{};
};

struct RecordingAwaiter {
  std::vector<std::string>& events;

  bool await_ready() {
    events.push_back("await_ready");
    return false;
  }

  bool await_suspend(std::coroutine_handle<>) {
    events.push_back("await_suspend");
    return false;
  }

  int await_resume() {
    events.push_back("await_resume");
    return 7;
  }
};

IntTask use_awaiter(std::vector<std::string>& events) {
  int value = co_await RecordingAwaiter{events};
  co_return value * 2;
}

TEST(Coroutines, GeneratorDoesNotRunUntilItIsResumed) {
  std::vector<std::string> events;
  IntGenerator generator = counting_sequence(events, 2);

  EXPECT_TRUE(events.empty());

  auto iterator = generator.begin();
  ASSERT_NE(iterator, generator.end());
  EXPECT_EQ(*iterator, 1);
  EXPECT_EQ(events, (std::vector<std::string>{"body started"}));

  ++iterator;
  ASSERT_NE(iterator, generator.end());
  EXPECT_EQ(*iterator, 2);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{"body started", "resumed after 1"}));

  ++iterator;
  EXPECT_EQ(iterator, generator.end());
  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "body started",
          "resumed after 1",
          "resumed after 2",
          "body completed",
      }));

  // initial_suspend 返回 suspend_always，所以调用函数只创建 coroutine frame。begin 和
  // ++ 恢复执行；每个 co_yield 经 promise.yield_value 保存值后再次暂停。
}

TEST(Coroutines, RangeForConsumesTheGeneratorProtocol) {
  std::vector<std::string> events;
  std::vector<int> values;

  for (int value : counting_sequence(events, 3)) {
    values.push_back(value);
  }

  EXPECT_EQ(values, (std::vector<int>{1, 2, 3}));
  EXPECT_EQ(events.back(), "body completed");

  // coroutine 不是线程；每次 resume 都在调用线程继续执行。generator 只是用 iterator
  // 协议包装 handle，让 range-for 驱动暂停点。
}

TEST(Coroutines, DestroyingASuspendedCoroutineDestroysItsFrameObjects) {
  std::vector<std::string> events;

  {
    IntGenerator generator = suspended_resource(events);
    auto iterator = generator.begin();
    EXPECT_EQ(*iterator, 7);
    EXPECT_EQ(events, (std::vector<std::string>{"frame resource acquired"}));
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "frame resource acquired",
          "frame resource released",
      }));

  // 局部变量通常存放在 coroutine frame 中，暂停跨越其作用域时继续存活。所有者必须
  // 最终 destroy handle；否则 frame、参数副本和已构造局部对象都会泄漏。
}

TEST(Coroutines, UnhandledExceptionIsStoredAndRethrownByTheConsumer) {
  IntGenerator generator = failing_sequence();
  auto iterator = generator.begin();

  EXPECT_EQ(*iterator, 3);
  EXPECT_THROW(++iterator, std::runtime_error);

  // 异常不会直接越过挂起边界；编译器调用 promise.unhandled_exception。generator 在
  // 恢复后检测保存的 exception_ptr，并在普通调用栈中重新抛给消费者。
}

TEST(Coroutines, AwaiterControlsWhetherAndHowSuspensionHappens) {
  std::vector<std::string> events;
  IntTask task = use_awaiter(events);

  EXPECT_EQ(task.result(), 14);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{"await_ready", "await_suspend", "await_resume"}));

  // await_ready 为 false 后调用 await_suspend；它返回 false 表示不要保持暂停，于是立即
  // 调用 await_resume 产生表达式结果。返回 void、bool 或另一个 handle 可表达不同调度。
}

}  // namespace
