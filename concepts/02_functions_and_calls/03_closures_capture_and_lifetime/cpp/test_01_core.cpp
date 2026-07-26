// 闭包捕获与生命周期。
// 共同问题：闭包捕获绑定还是值；循环创建的函数看到哪个变量；捕获状态能否修改；
// 外层调用结束后状态是否仍存活。
//
// polyglot-family: functions_and_calls
// polyglot-concept: closures_capture_and_lifetime
// polyglot-related: languages/cpp/language/test_007_lambda_captures_generic_and_constexpr.cpp
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <functional>
#include <memory>
#include <type_traits>
#include <vector>

namespace {

TEST(ClosureCaptureConcept, ValueCaptureStoresAClosureOwnedSnapshot) {
  int source = 1;
  auto read = [source] { return source; };

  source = 2;

  EXPECT_EQ(read(), 1);
  static_assert(std::is_copy_constructible_v<decltype(read)>);
}

TEST(ClosureCaptureConcept, ReferenceCaptureObservesLaterChanges) {
  int source = 1;
  auto read = [&source] { return source; };

  source = 2;

  EXPECT_EQ(read(), 2);

  // 引用捕获不延长 source 生命周期；返回这种 lambda 后调用可能悬垂，这里不构造危险案例。
}

TEST(ClosureCaptureConcept, MutableValueCaptureMaintainsPrivateState) {
  auto counter = [count = 0]() mutable {
    count += 1;
    return count;
  };

  EXPECT_EQ(counter(), 1);
  EXPECT_EQ(counter(), 2);
}

TEST(ClosureCaptureConcept, LoopCaptureModeControlsPerFunctionResults) {
  std::vector<std::function<int()>> snapshots;
  for (int index = 0; index < 3; ++index) {
    snapshots.push_back([index] { return index; });
  }

  EXPECT_EQ(snapshots[0](), 0);
  EXPECT_EQ(snapshots[1](), 1);
  EXPECT_EQ(snapshots[2](), 2);
}

TEST(ClosureCaptureConcept, SharedOwnershipCanExtendCapturedObjectLifetime) {
  auto state = std::make_shared<int>(1);
  auto read = [state] { return *state; };
  state.reset();

  EXPECT_EQ(read(), 1);
}

}  // namespace
