// polyglot-covers:
// - cpp.stdlib.cfenv.exception-flags-clear-raise-test-and-restore
// - cpp.stdlib.cfenv.rounding-direction-query-and-change
// - cpp.stdlib.cfenv.environment-save-hold-set-and-update
// - cpp.stdlib.cmath.nearbyint-rint-and-current-rounding-mode
// - cpp.stdlib.cmath.round-lround-and-rounding-mode-independence
// - cpp.stdlib.cmath.floor-ceil-trunc-directional-rounding
// - cpp.stdlib.cmath.math-errhandling-domain-and-pole-errors
// - cpp.stdlib.cmath.floating-environment-is-thread-local-state

#include <gtest/gtest.h>

#include <cerrno>
#include <cfenv>
#include <cmath>

namespace {

class FloatingEnvironmentTest : public ::testing::Test {
 protected:
  void SetUp() override {
    ASSERT_EQ(std::fegetenv(&original_environment_), 0);
    ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
    ASSERT_EQ(std::fesetround(FE_TONEAREST), 0);
  }

  void TearDown() override {
    // 舍入方向和异常标志属于线程的浮点环境。每个案例都恢复进入测试前的完整状态，避免
    // 一个测试改变后续测试的数值结果。
    EXPECT_EQ(std::fesetenv(&original_environment_), 0);
  }

 private:
  std::fenv_t original_environment_{};
};

TEST_F(FloatingEnvironmentTest, ExceptionFlagsCanBeRaisedInspectedAndCleared) {
  EXPECT_EQ(std::fetestexcept(FE_ALL_EXCEPT), 0);

  ASSERT_EQ(std::feraiseexcept(FE_INVALID | FE_DIVBYZERO), 0);
  EXPECT_NE(std::fetestexcept(FE_INVALID), 0);
  EXPECT_NE(std::fetestexcept(FE_DIVBYZERO), 0);

  ASSERT_EQ(std::feclearexcept(FE_INVALID), 0);
  EXPECT_EQ(std::fetestexcept(FE_INVALID), 0);
  EXPECT_NE(std::fetestexcept(FE_DIVBYZERO), 0);

  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
  EXPECT_EQ(std::fetestexcept(FE_ALL_EXCEPT), 0);

  // 浮点异常默认是“粘滞标志”，不是 C++ exception。标志一旦升起会保留到显式清除；
  // 读取标志也不会消费它。
}

TEST_F(FloatingEnvironmentTest, ExceptionFlagObjectsCopySelectedFlags) {
  ASSERT_EQ(std::feraiseexcept(FE_OVERFLOW | FE_INEXACT), 0);

  std::fexcept_t saved_flags{};
  ASSERT_EQ(std::fegetexceptflag(&saved_flags, FE_OVERFLOW | FE_INEXACT), 0);
  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
  EXPECT_EQ(std::fetestexcept(FE_ALL_EXCEPT), 0);

  ASSERT_EQ(std::fesetexceptflag(&saved_flags, FE_OVERFLOW | FE_INEXACT), 0);
  EXPECT_NE(std::fetestexcept(FE_OVERFLOW), 0);
  EXPECT_NE(std::fetestexcept(FE_INEXACT), 0);
  EXPECT_EQ(std::fetestexcept(FE_INVALID), 0);

  // fexcept_t 是供库函数往返传递的表示，不应自行解释其位布局；第二个参数决定保存和
  // 恢复哪些标准异常标志。
}

TEST_F(FloatingEnvironmentTest, SupportedRoundingDirectionsRoundTripThroughTheApi) {
  const int modes[] = {
      FE_TONEAREST,
      FE_DOWNWARD,
      FE_UPWARD,
      FE_TOWARDZERO,
  };

  for (const int mode : modes) {
    ASSERT_EQ(std::fesetround(mode), 0);
    EXPECT_EQ(std::fegetround(), mode);
  }

  // 不要假定宏的整数值或顺序；只能把实现提供的 FE_* 常量交回接口。fesetround 对不受
  // 支持的值返回非零，但当前锁定的 IEC 60559 工具链支持以上四种标准方向。
}

TEST_F(FloatingEnvironmentTest, NearbyintUsesTheCurrentDirectionWithoutRaisingInexact) {
  volatile double positive_input = 2.5;
  volatile double negative_input = -2.5;

  ASSERT_EQ(std::fesetround(FE_DOWNWARD), 0);
  EXPECT_DOUBLE_EQ(std::nearbyint(positive_input), 2.0);
  EXPECT_DOUBLE_EQ(std::nearbyint(negative_input), -3.0);
  EXPECT_EQ(std::fetestexcept(FE_INEXACT), 0);

  ASSERT_EQ(std::fesetround(FE_UPWARD), 0);
  EXPECT_DOUBLE_EQ(std::nearbyint(positive_input), 3.0);
  EXPECT_DOUBLE_EQ(std::nearbyint(negative_input), -2.0);
  EXPECT_EQ(std::fetestexcept(FE_INEXACT), 0);

  // volatile 阻止测试输入被直接折叠成常量。nearbyint 按当前模式舍入，并特意不升起
  // FE_INEXACT，适合只需要舍入值而不想污染异常状态的工作流。
}

TEST_F(FloatingEnvironmentTest, RintMayRaiseInexactForANonIntegralInput) {
  volatile double input = 2.25;
  ASSERT_EQ(std::fesetround(FE_TONEAREST), 0);
  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);

  EXPECT_DOUBLE_EQ(std::rint(input), 2.0);
  EXPECT_NE(std::fetestexcept(FE_INEXACT), 0);

  // rint 与 nearbyint 的值语义相同，关键差别是 rint 对不精确结果可以升起
  // FE_INEXACT。若代码观察浮点环境，两者不能仅凭返回值互换。
}

TEST_F(FloatingEnvironmentTest, RoundIgnoresTheCurrentRoundingDirection) {
  ASSERT_EQ(std::fesetround(FE_DOWNWARD), 0);

  EXPECT_DOUBLE_EQ(std::round(2.5), 3.0);
  EXPECT_DOUBLE_EQ(std::round(-2.5), -3.0);
  EXPECT_EQ(std::lround(2.5), 3L);
  EXPECT_EQ(std::lround(-2.5), -3L);

  ASSERT_EQ(std::fesetround(FE_UPWARD), 0);
  EXPECT_DOUBLE_EQ(std::round(2.5), 3.0);
  EXPECT_DOUBLE_EQ(std::round(-2.5), -3.0);

  // round/lround 固定采用“中点远离零”，不读取当前舍入方向；它们和采用 bankers
  // rounding 的语言 API 也不一定一致。
}

TEST_F(FloatingEnvironmentTest, FloorCeilAndTruncHaveNamedDirections) {
  ASSERT_EQ(std::fesetround(FE_DOWNWARD), 0);

  EXPECT_DOUBLE_EQ(std::floor(2.9), 2.0);
  EXPECT_DOUBLE_EQ(std::floor(-2.1), -3.0);
  EXPECT_DOUBLE_EQ(std::ceil(2.1), 3.0);
  EXPECT_DOUBLE_EQ(std::ceil(-2.9), -2.0);
  EXPECT_DOUBLE_EQ(std::trunc(2.9), 2.0);
  EXPECT_DOUBLE_EQ(std::trunc(-2.9), -2.0);

  // floor 向负无穷、ceil 向正无穷、trunc 向零；这些方向由函数名定义，不受当前环境的
  // FE_DOWNWARD 影响。
}

TEST_F(FloatingEnvironmentTest, HoldClearsFlagsAndSetEnvDiscardsLaterFlags) {
  ASSERT_EQ(std::feraiseexcept(FE_DIVBYZERO), 0);

  std::fenv_t saved_environment{};
  ASSERT_EQ(std::feholdexcept(&saved_environment), 0);
  EXPECT_EQ(std::fetestexcept(FE_ALL_EXCEPT), 0);

  ASSERT_EQ(std::feraiseexcept(FE_OVERFLOW), 0);
  ASSERT_EQ(std::fesetenv(&saved_environment), 0);
  EXPECT_NE(std::fetestexcept(FE_DIVBYZERO), 0);
  EXPECT_EQ(std::fetestexcept(FE_OVERFLOW), 0);

  // feholdexcept 保存环境、清除标志并尝试进入 non-stop 模式；fesetenv 直接安装保存值，
  // 因而 hold 之后新产生的 FE_OVERFLOW 被丢弃。
}

TEST_F(FloatingEnvironmentTest, UpdateEnvMergesCurrentExceptionsIntoSavedState) {
  ASSERT_EQ(std::feraiseexcept(FE_DIVBYZERO), 0);
  std::fenv_t saved_environment{};
  ASSERT_EQ(std::fegetenv(&saved_environment), 0);

  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
  ASSERT_EQ(std::feraiseexcept(FE_INVALID), 0);
  ASSERT_EQ(std::feupdateenv(&saved_environment), 0);

  EXPECT_NE(std::fetestexcept(FE_DIVBYZERO), 0);
  EXPECT_NE(std::fetestexcept(FE_INVALID), 0);

  // feupdateenv 先记住当前异常，再安装目标环境，最后重新升起刚才记住的异常；它适合
  // 临时环境结束时传播异常。只想回滚时应使用 fesetenv。
}

TEST_F(FloatingEnvironmentTest, DomainErrorsFollowTheAdvertisedMathPolicy) {
  errno = 0;
  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
  volatile double negative = -1.0;

  const double result = std::sqrt(negative);
  EXPECT_TRUE(std::isnan(result));

  if ((math_errhandling & MATH_ERRNO) != 0) {
    EXPECT_EQ(errno, EDOM);
  }
  if ((math_errhandling & MATH_ERREXCEPT) != 0) {
    EXPECT_NE(std::fetestexcept(FE_INVALID), 0);
  }

  // math_errhandling 是实现策略位掩码：实现可用 errno、浮点异常或两者报告错误。代码
  // 必须先检查策略，不能无条件假定某一种通道。
}

TEST_F(FloatingEnvironmentTest, PoleErrorsAreDifferentFromDomainErrors) {
  errno = 0;
  ASSERT_EQ(std::feclearexcept(FE_ALL_EXCEPT), 0);
  volatile double zero = 0.0;

  const double result = std::log(zero);
  EXPECT_TRUE(std::isinf(result));
  EXPECT_TRUE(std::signbit(result));

  if ((math_errhandling & MATH_ERRNO) != 0) {
    EXPECT_EQ(errno, ERANGE);
  }
  if ((math_errhandling & MATH_ERREXCEPT) != 0) {
    EXPECT_NE(std::fetestexcept(FE_DIVBYZERO), 0);
  }

  // log(0) 是 pole error，典型结果为负无穷；sqrt(-1) 则是 domain error 和 NaN。
  // errno 的类别以及浮点异常标志都不同。
}

}  // namespace
