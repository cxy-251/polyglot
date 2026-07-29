// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_113_duration_monotonic_and_wall_time_test.go
//
// 共同问题：duration 的单位与范围是什么；时间点相减使用 wall clock 还是 monotonic clock。
// 对照观察：Go Duration 是 int64 纳秒数；同一进程的 time.Now 值携带可用于 Sub 的 monotonic reading。
package durations_clocks_and_monotonic_time

import (
	"testing"
	"time"
)

func TestDurationHasExplicitUnitsAndArithmetic(t *testing.T) {
	duration := 1500*time.Millisecond + 2*time.Second
	if duration != 3500*time.Millisecond || duration.Seconds() != 3.5 {
		t.Fatal("单位常量在编译期形成同一个纳秒计数")
	}
	base := time.Now()
	later := base.Add(duration)
	if later.Sub(base) != duration {
		t.Fatal("Add/Sub 在两值都含 monotonic reading 时避免 wall clock 调整影响")
	}
}

func TestWallOnlyCopyRepresentsSameInstantButDifferentInternalState(t *testing.T) {
	now := time.Now()
	wallOnly := now.Round(0)
	if !now.Equal(wallOnly) || now == wallOnly {
		t.Fatal("monotonic component 不属于可移植 wall timestamp，但参与 Time 的 ==")
	}
	if time.Duration(1500).Milliseconds() != 0 {
		t.Fatal("裸 Duration 数字单位是纳秒；跨 API 必须显式乘单位常量")
	}
}
