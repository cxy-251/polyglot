// polyglot-covers:
// - cpp.stdlib.concurrency.stop-source-token-shared-state-and-idempotent-request
// - cpp.stdlib.concurrency.stop-source-nostopstate-and-stop-possible
// - cpp.stdlib.concurrency.stop-callback-synchronous-invocation-and-thread-identity
// - cpp.stdlib.concurrency.stop-callback-registration-after-request
// - cpp.stdlib.concurrency.stop-callback-destructor-waits-for-running-callback
// - cpp.stdlib.concurrency.stop-callback-order-and-throwing-terminate-traps
// - cpp.stdlib.concurrency.jthread-stop-token-injection-and-explicit-request
// - cpp.stdlib.concurrency.jthread-callable-without-stop-token
// - cpp.stdlib.concurrency.jthread-destructor-request-stop-and-join
// - cpp.stdlib.concurrency.jthread-stop-source-token-and-move-only-ownership

#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <memory>
#include <stop_token>
#include <thread>
#include <utility>

namespace {

struct BlockingCallback {
  std::promise<void>* entered;
  std::shared_future<void> release;

  void operator()() const {
    entered->set_value();
    release.wait();
  }
};

TEST(StopSourceAndToken, CopiesShareOneIdempotentCancellationState) {
  std::stop_source source;
  std::stop_source source_copy = source;
  const std::stop_token token = source.get_token();

  EXPECT_TRUE(source.stop_possible());
  EXPECT_TRUE(token.stop_possible());
  EXPECT_FALSE(token.stop_requested());
  EXPECT_EQ(source_copy, source);
  EXPECT_TRUE(source_copy.request_stop());
  EXPECT_TRUE(token.stop_requested());
  EXPECT_FALSE(source.request_stop());

  // source/token 是共享停止状态的句柄；首次 request_stop 返回 true，后续请求只
  // 观察到已经停止并返回 false。停止是单向状态，不能重置后复用同一代任务。
}

TEST(StopSourceAndToken, NostopstateRepresentsWorkThatCannotBeCancelled) {
  std::stop_source disabled{std::nostopstate};
  const std::stop_token token = disabled.get_token();

  EXPECT_FALSE(disabled.stop_possible());
  EXPECT_FALSE(disabled.stop_requested());
  EXPECT_FALSE(disabled.request_stop());
  EXPECT_FALSE(token.stop_possible());
  EXPECT_FALSE(token.stop_requested());
  EXPECT_EQ(token, std::stop_token{});

  // stop_possible=false 不等于“当前还没请求”，而是根本没有共享停止状态。算法可
  // 借此跳过回调注册，但仍应让无取消路径产生与正常完成相同的结果语义。
}

TEST(StopCallback, RequestStopRunsRegisteredCallbacksSynchronously) {
  std::stop_source source;
  const std::stop_token token = source.get_token();
  int calls = 0;
  std::thread::id callback_thread;
  const auto requesting_thread = std::this_thread::get_id();
  std::stop_callback callback{token, [&] {
    ++calls;
    callback_thread = std::this_thread::get_id();
  }};

  EXPECT_TRUE(source.request_stop());
  EXPECT_EQ(calls, 1);
  EXPECT_EQ(callback_thread, requesting_thread);
  EXPECT_FALSE(source.request_stop());
  EXPECT_EQ(calls, 1);

  // 本例没有并发请求，所以回调就在 request_stop 调用线程内同步完成；一般情况下
  // 也可能由已开始执行它的另一线程完成。request_stop 返回时相关回调已经处理完。
}

TEST(StopCallback, RegisteringAfterARequestInvokesTheCallbackBeforeConstructionReturns) {
  std::stop_source source;
  const auto token = source.get_token();
  ASSERT_TRUE(source.request_stop());
  int calls = 0;

  std::stop_callback callback{token, [&] { ++calls; }};

  EXPECT_EQ(calls, 1);

  // 先检查 stop_requested 再注册存在竞态；stop_callback 把检查和注册合并。状态已
  // 停止时，构造函数会在返回前调用回调，因此回调不得依赖“对象已构造完”的后续代码。
}

TEST(StopCallback, DestructionWaitsUntilAConcurrentCallbackFinishes) {
  std::stop_source source;
  std::promise<void> entered;
  auto entered_future = entered.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  using Callback = std::stop_callback<BlockingCallback>;
  auto callback = std::make_unique<Callback>(
      source.get_token(),
      BlockingCallback{&entered, release_future});

  std::thread requester{[&source] { source.request_stop(); }};
  entered_future.wait();

  std::promise<void> destroyed;
  auto destroyed_future = destroyed.get_future();
  std::thread destroyer{[&] {
    callback.reset();
    destroyed.set_value();
  }};
  EXPECT_EQ(
      destroyed_future.wait_for(std::chrono::seconds::zero()),
      std::future_status::timeout);

  release.set_value();
  requester.join();
  destroyer.join();
  EXPECT_EQ(
      destroyed_future.wait_for(std::chrono::seconds::zero()),
      std::future_status::ready);

  // 析构会注销尚未开始的回调；若回调正在其他线程执行，则等它结束，保证回调不再
  // 访问已销毁的捕获状态。回调之间顺序未指定，且抛异常会 terminate。
}

TEST(JthreadCancellation, TokenAwareCallableObservesAnExplicitStopRequest) {
  std::promise<void> started;
  auto started_future = started.get_future();
  std::promise<void> release;
  auto release_future = release.get_future().share();
  std::promise<bool> observed;
  auto observed_future = observed.get_future();

  std::jthread worker{
      [&started, release_future, &observed](std::stop_token token, int factor) {
        started.set_value();
        release_future.wait();
        observed.set_value(token.stop_requested() && factor == 2);
      },
      2};
  started_future.wait();
  EXPECT_TRUE(worker.get_stop_token().stop_possible());
  EXPECT_TRUE(worker.request_stop());
  release.set_value();
  EXPECT_TRUE(observed_future.get());
  worker.join();

  // 若 callable 可用 stop_token 作为首参调用，jthread 自动注入自己的 token，后续
  // 参数仍按 thread 的 decay-copy 规则传递。request_stop 只是请求，任务必须协作退出。
}

TEST(JthreadConstruction, CallableWithoutStopTokenStillUsesOrdinaryInvokeRules) {
  std::promise<int> result;
  auto future = result.get_future();
  std::jthread worker{[&result](int value) { result.set_value(value * 2); }, 21};

  EXPECT_EQ(future.get(), 42);
  worker.join();

  // jthread 先判断“注入 token 后是否可调用”，否则按普通参数调用；这不是运行时
  // 重载选择。设计同时接受两种签名的泛型 callable 时要留意哪一个会被选中。
}

TEST(JthreadLifetime, DestructorRequestsStopThenJoinsTheOwnedThread) {
  std::promise<void> callback_registered;
  auto registered_future = callback_registered.get_future();
  std::promise<void> stop_signal;
  auto stop_future = stop_signal.get_future().share();
  std::promise<bool> returned_after_stop;
  auto returned_future = returned_after_stop.get_future();

  {
    std::jthread worker{[&](std::stop_token token) {
      std::stop_callback callback{token, [&stop_signal] {
        stop_signal.set_value();
      }};
      callback_registered.set_value();
      stop_future.wait();
      returned_after_stop.set_value(token.stop_requested());
    }};
    registered_future.wait();
  }

  EXPECT_TRUE(returned_future.get());

  // joinable jthread 析构先 request_stop 再 join，适合结构化并发；若任务忽略 token
  // 或永久阻塞，析构仍会永久等待。自动 join 不是强制取消机制。
}

TEST(JthreadOwnership, MoveTransfersBothThreadAndStopStateHandles) {
  std::promise<void> release;
  auto ready = release.get_future().share();
  std::jthread original{[ready](std::stop_token) { ready.wait(); }};
  const auto token = original.get_stop_token();
  auto source = original.get_stop_source();

  std::jthread owner = std::move(original);
  EXPECT_FALSE(original.joinable());
  EXPECT_TRUE(owner.joinable());
  EXPECT_EQ(owner.get_stop_token(), token);
  EXPECT_EQ(owner.get_stop_source(), source);
  EXPECT_TRUE(source.request_stop());
  EXPECT_TRUE(owner.get_stop_token().stop_requested());
  release.set_value();
  owner.join();

  // 移动 jthread 同时转移执行线程和其 stop_source；外部已复制的 token/source 仍
  // 指向同一停止状态。它们不能延长系统线程寿命，只延长停止状态本身。
}

}  // namespace
