// polyglot-covers:
// - cpp.stdlib.ctime.time-current-value-output-parameter-and-time-t-opacity
// - cpp.stdlib.ctime.difftime-portable-time-t-difference
// - cpp.stdlib.ctime.timespec-get-time-utc-and-nanosecond-range
// - cpp.stdlib.ctime.clock-process-cpu-time-and-clock-t-failure
// - cpp.stdlib.ctime.tm-field-ranges-gmtime-and-localtime
// - cpp.stdlib.ctime.mktime-local-interpretation-normalization-and-derived-fields
// - cpp.stdlib.ctime.mktime-localtime-round-trip
// - cpp.stdlib.ctime.strftime-numeric-format-and-small-buffer-failure
// - cpp.stdlib.ctime.asctime-fixed-layout-and-static-storage
// - cpp.stdlib.ctime.ctime-local-convenience-and-static-storage
// - cpp.stdlib.ctime.thread-safety-and-copy-immediately-trap

#include <gtest/gtest.h>

#include <array>
#include <ctime>
#include <string>
#include <type_traits>

namespace {

void ExpectTmFieldsInRange(const std::tm& value) {
  EXPECT_GE(value.tm_sec, 0);
  EXPECT_LE(value.tm_sec, 60);
  EXPECT_GE(value.tm_min, 0);
  EXPECT_LE(value.tm_min, 59);
  EXPECT_GE(value.tm_hour, 0);
  EXPECT_LE(value.tm_hour, 23);
  EXPECT_GE(value.tm_mday, 1);
  EXPECT_LE(value.tm_mday, 31);
  EXPECT_GE(value.tm_mon, 0);
  EXPECT_LE(value.tm_mon, 11);
  EXPECT_GE(value.tm_wday, 0);
  EXPECT_LE(value.tm_wday, 6);
  EXPECT_GE(value.tm_yday, 0);
  EXPECT_LE(value.tm_yday, 365);
}

TEST(CTimeNow, TimeReturnsAndOptionallyStoresTheSameCurrentValue) {
  std::time_t stored{};
  const std::time_t returned = std::time(&stored);

  EXPECT_EQ(returned, stored);
  static_assert(std::is_arithmetic_v<std::time_t>);

  // time_t 是实现定义的算术表示，不保证是 Unix 秒数、整数或特定宽度。需要求差时使用
  // difftime，需要日历字段时使用 gmtime/localtime。
}

TEST(CTimeDifference, DifftimeAvoidsAssumingTimeTSupportsMeaningfulSubtraction) {
  const std::time_t now = std::time(nullptr);

  EXPECT_DOUBLE_EQ(std::difftime(now, now), 0.0);

  // 即使某实现的 time_t 可直接相减，可移植代码也应让 difftime 解释单位和表示。
}

TEST(CTimeTimespec, TimespecGetFillsSecondsAndANormalizedNanosecondPart) {
  std::timespec value{};
  const int base = std::timespec_get(&value, TIME_UTC);

  ASSERT_EQ(base, TIME_UTC);
  EXPECT_GE(value.tv_nsec, 0L);
  EXPECT_LT(value.tv_nsec, 1'000'000'000L);

  // TIME_UTC 是当前标准定义的时间基准；成功时函数返回该 base。timespec 分开保存整秒
  // 和 [0,10^9) 纳秒余数，但 tv_sec 的 epoch 仍由 time_t 实现定义。
}

TEST(CTimeClock, ClockReportsProcessCpuTimeOrTheDocumentedFailureValue) {
  const std::clock_t first = std::clock();
  const std::clock_t second = std::clock();

  static_assert(CLOCKS_PER_SEC > 0);
  if (first != static_cast<std::clock_t>(-1) &&
      second != static_cast<std::clock_t>(-1)) {
    EXPECT_GE(second, first);
    const double cpu_seconds =
        static_cast<double>(second - first) / CLOCKS_PER_SEC;
    EXPECT_GE(cpu_seconds, 0.0);
  } else {
    SUCCEED() << "该实现本次无法取得进程 CPU 时间";
  }

  // clock 测量实现定义 epoch 起的进程 CPU 时间，不是墙钟时间；失败返回 clock_t(-1)。
  // 不用 sleep 检测它，因为休眠通常不消耗进程 CPU。
}

TEST(CTimeBrokenDown, GmtimeAndLocaltimeProduceCalendarFieldsForCurrentTime) {
  const std::time_t now = std::time(nullptr);
  const std::tm* utc_pointer = std::gmtime(&now);
  ASSERT_NE(utc_pointer, nullptr);
  const std::tm utc_copy = *utc_pointer;

  const std::tm* local_pointer = std::localtime(&now);
  ASSERT_NE(local_pointer, nullptr);
  const std::tm local_copy = *local_pointer;

  ExpectTmFieldsInRange(utc_copy);
  ExpectTmFieldsInRange(local_copy);

  // gmtime/localtime 可复用同一静态对象，下一次调用甚至可能覆盖前一次结果；必须像这里
  // 一样立即按值复制。标准也不要求这些函数避免数据竞争，多线程代码应使用平台安全
  // 版本或更高层 chrono API。
}

TEST(CTimeBrokenDown, TmUsesZeroBasedMonthAndYearsSince1900) {
  std::tm value{};
  value.tm_year = 2024 - 1900;
  value.tm_mon = 6 - 1;
  value.tm_mday = 15;
  value.tm_hour = 13;
  value.tm_min = 30;
  value.tm_sec = 45;

  EXPECT_EQ(value.tm_year, 124);
  EXPECT_EQ(value.tm_mon, 5);

  // tm_mon 是 [0,11]，tm_year 是自 1900 起的年数；这两个偏移是 C 时间 API 最常见的
  // off-by-one 来源。tm_wday/tm_yday 在 mktime 前尚未由这些字段自动计算。
}

TEST(CTimeMktime, ItInterpretsLocalTimeAndNormalizesOutOfRangeFields) {
  std::tm value{};
  value.tm_year = 2024 - 1900;
  value.tm_mon = 12;
  value.tm_mday = 1;
  value.tm_hour = 12;
  value.tm_isdst = -1;

  const std::time_t encoded = std::mktime(&value);

  ASSERT_NE(encoded, static_cast<std::time_t>(-1));
  EXPECT_EQ(value.tm_year, 2025 - 1900);
  EXPECT_EQ(value.tm_mon, 0);
  EXPECT_EQ(value.tm_mday, 1);
  ExpectTmFieldsInRange(value);

  // tm_mon=12 被归一化成下一年一月。mktime 把字段解释为本地时间并原地写回规范字段、
  // weekday 和 yearday；tm_isdst=-1 请求实现自行判断夏令时。
}

TEST(CTimeMktime, LocaltimeRoundTripsARepresentableLocalCivilValue) {
  std::tm input{};
  input.tm_year = 2024 - 1900;
  input.tm_mon = 6 - 1;
  input.tm_mday = 15;
  input.tm_hour = 12;
  input.tm_min = 34;
  input.tm_sec = 56;
  input.tm_isdst = -1;

  const std::time_t encoded = std::mktime(&input);
  ASSERT_NE(encoded, static_cast<std::time_t>(-1));
  const std::tm* decoded_pointer = std::localtime(&encoded);
  ASSERT_NE(decoded_pointer, nullptr);
  const std::tm decoded = *decoded_pointer;

  EXPECT_EQ(decoded.tm_year, 2024 - 1900);
  EXPECT_EQ(decoded.tm_mon, 6 - 1);
  EXPECT_EQ(decoded.tm_mday, 15);
  EXPECT_EQ(decoded.tm_hour, 12);
  EXPECT_EQ(decoded.tm_min, 34);
  EXPECT_EQ(decoded.tm_sec, 56);

  // 选择中午避免落入常见 DST 缺口/重叠。对切换边界的本地时间，tm_isdst 选择会影响
  // 映射，C API 没有 chrono ambiguous/nonexistent 异常那样清晰的诊断。
}

TEST(CTimeFormatting, StrftimeFormatsNumericFieldsIntoACallerOwnedBuffer) {
  std::tm value{};
  value.tm_year = 2024 - 1900;
  value.tm_mon = 2 - 1;
  value.tm_mday = 29;
  value.tm_hour = 5;
  value.tm_min = 6;
  value.tm_sec = 7;
  std::array<char, 32> buffer{};

  const std::size_t count = std::strftime(
      buffer.data(), buffer.size(), "%Y-%m-%d %H:%M:%S", &value);

  ASSERT_EQ(count, 19U);
  EXPECT_EQ(std::string{buffer.data()}, "2024-02-29 05:06:07");

  // 返回值不含结尾 NUL。数值格式不依赖月份名称翻译；%a/%B 等文本字段由当前 C locale
  // 决定。
}

TEST(CTimeFormatting, StrftimeReturnsZeroWhenTheResultDoesNotFit) {
  std::tm value{};
  value.tm_year = 2024 - 1900;
  value.tm_mon = 0;
  value.tm_mday = 1;
  std::array<char, 5> too_small{};

  EXPECT_EQ(std::strftime(
                too_small.data(), too_small.size(), "%Y-%m-%d", &value),
            0U);

  // 返回 0 时缓冲区内容不能当作完整字符串使用；调用者应扩大容量或改用类型安全格式化。
}

TEST(CTimeText, AsctimeUsesAFixedLegacyLayoutAndStaticStorage) {
  std::tm value{};
  value.tm_year = 2022 - 1900;
  value.tm_mon = 0;
  value.tm_mday = 2;
  value.tm_hour = 3;
  value.tm_min = 4;
  value.tm_sec = 5;
  value.tm_wday = 0;

  const char* pointer = std::asctime(&value);
  ASSERT_NE(pointer, nullptr);
  const std::string copied{pointer};

  EXPECT_EQ(copied, "Sun Jan  2 03:04:05 2022\n");
  EXPECT_EQ(copied.size(), 25U);

  // asctime 返回静态数组，格式固定且包含换行；字段超出可表示布局还可能导致未定义行为。
  // 立即复制，不要保存裸指针。
}

TEST(CTimeText, CtimeCombinesLocaltimeAndAsctimeForATimeT) {
  const std::time_t now = std::time(nullptr);
  const char* pointer = std::ctime(&now);
  ASSERT_NE(pointer, nullptr);
  const std::string copied{pointer};

  EXPECT_FALSE(copied.empty());
  EXPECT_EQ(copied.back(), '\n');

  // ctime 等价于本地分解再用 asctime 格式化，继承本地时区、静态缓冲区和线程安全问题；
  // 它适合诊断文本，不适合稳定协议。
}

}  // namespace
