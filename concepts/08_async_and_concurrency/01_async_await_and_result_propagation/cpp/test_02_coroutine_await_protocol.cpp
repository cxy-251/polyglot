// 异步等待与结果传播。
// 共同问题：异步函数调用何时开始执行；await 如何取得结果；失败如何传播；
// 多个结果如何组合。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/cpp/language/test_021_coroutines_promise_awaiter_and_generator.cpp

#include <gtest/gtest.h>

#include <coroutine>
#include <exception>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

namespace {

class EventLog {
 public:
  void add(std::string_view event) {
    events_.push_back(event);
  }

  const std::vector<std::string_view>& values() const noexcept {
    return events_;
  }

 private:
  std::vector<std::string_view> events_;
};

template <bool Lazy>
class RecordingTask {
 public:
  struct promise_type;
  using Handle = std::coroutine_handle<promise_type>;

  struct InitialAwaiter {
    EventLog& events;

    bool await_ready() noexcept {
      events.add("initial await_ready");
      return !Lazy;
    }

    void await_suspend(std::coroutine_handle<>) noexcept {
      events.add("initial await_suspend");
    }

    void await_resume() noexcept {
      events.add("initial await_resume");
    }
  };

  struct promise_type {
    explicit promise_type(EventLog& log) : events(log) {
      events.add("promise constructed");
    }

    ~promise_type() {
      events.add("promise destroyed");
    }

    RecordingTask get_return_object() {
      events.add("get return object");
      return RecordingTask{Handle::from_promise(*this)};
    }

    InitialAwaiter initial_suspend() noexcept {
      events.add("initial_suspend");
      return InitialAwaiter{events};
    }

    std::suspend_always final_suspend() noexcept {
      events.add("final_suspend");
      return {};
    }

    void return_value(int value) noexcept {
      result = value;
      events.add("return_value");
    }

    void unhandled_exception() noexcept {
      failure = std::current_exception();
      events.add("unhandled_exception");
    }

    EventLog& events;
    int result{0};
    std::exception_ptr failure;
  };

  RecordingTask(const RecordingTask&) = delete;
  RecordingTask& operator=(const RecordingTask&) = delete;

  RecordingTask(RecordingTask&& other) noexcept
      : coroutine_(std::exchange(other.coroutine_, {})) {}

  ~RecordingTask() {
    if (coroutine_) {
      coroutine_.promise().events.add("destroy frame");
      coroutine_.destroy();
    }
  }

  void resume() {
    coroutine_.promise().events.add("owner resume");
    coroutine_.resume();
  }

  bool done() const {
    return coroutine_.done();
  }

  int result() const {
    if (coroutine_.promise().failure) {
      std::rethrow_exception(coroutine_.promise().failure);
    }
    return coroutine_.promise().result;
  }

 private:
  explicit RecordingTask(Handle coroutine) : coroutine_(coroutine) {}
  Handle coroutine_{};
};

struct RecordingAwaiter {
  EventLog& events;

  bool await_ready() noexcept {
    events.add("await_ready");
    return false;
  }

  bool await_suspend(std::coroutine_handle<>) noexcept {
    events.add("await_suspend");
    return false;
  }

  int await_resume() noexcept {
    events.add("await_resume");
    return 7;
  }
};

RecordingTask<true> lazy_value(EventLog& events) {
  events.add("body");
  const int value = co_await RecordingAwaiter{events};
  co_return value * 2;
}

RecordingTask<false> eager_value(EventLog& events) {
  events.add("body");
  co_return 42;
}

RecordingTask<true> lazy_failure(EventLog& events) {
  events.add("body");
  throw std::runtime_error{"coroutine failure"};
  co_return 0;
}

TEST(CoroutineAwaitConcept, LazyTaskStartsOnlyWhenItsHandleIsResumed) {
  EventLog events;
  {
    RecordingTask<true> task = lazy_value(events);

    EXPECT_EQ(
        events.values(),
        (std::vector<std::string_view>{
            "promise constructed",
            "get return object",
            "initial_suspend",
            "initial await_ready",
            "initial await_suspend",
        }));

    task.resume();

    EXPECT_TRUE(task.done());
    EXPECT_EQ(task.result(), 14);
    EXPECT_EQ(
        events.values(),
        (std::vector<std::string_view>{
            "promise constructed",
            "get return object",
            "initial_suspend",
            "initial await_ready",
            "initial await_suspend",
            "owner resume",
            "initial await_resume",
            "body",
            "await_ready",
            "await_suspend",
            "await_resume",
            "return_value",
            "final_suspend",
        }));
  }

  EXPECT_EQ(
      events.values().end()[-2],
      "destroy frame");
  EXPECT_EQ(events.values().back(), "promise destroyed");
}

TEST(CoroutineAwaitConcept, EagerTaskRunsBeforeTheCallReturns) {
  EventLog events;
  RecordingTask<false> task = eager_value(events);

  EXPECT_TRUE(task.done());
  EXPECT_EQ(task.result(), 42);
  EXPECT_EQ(
      events.values(),
      (std::vector<std::string_view>{
          "promise constructed",
          "get return object",
          "initial_suspend",
          "initial await_ready",
          "initial await_resume",
          "body",
          "return_value",
          "final_suspend",
      }));

  // initial_suspend 的 await_ready 决定调用是 eager 还是 lazy；coroutine 本身不提供
  // 线程或事件循环，外部所有者仍须保存 handle 并最终 destroy frame。
}

TEST(CoroutineAwaitConcept, UnhandledExceptionIsStoredByPromiseAndRethrownByOwner) {
  EventLog events;
  RecordingTask<true> task = lazy_failure(events);

  task.resume();

  EXPECT_TRUE(task.done());
  EXPECT_THROW(static_cast<void>(task.result()), std::runtime_error);
  EXPECT_EQ(
      events.values().end()[-2],
      "unhandled_exception");
  EXPECT_EQ(events.values().back(), "final_suspend");
}

}  // namespace
