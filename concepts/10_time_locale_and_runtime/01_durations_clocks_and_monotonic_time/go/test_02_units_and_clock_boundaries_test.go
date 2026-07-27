// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_113_duration_monotonic_and_wall_time_test.go
//
// 共同问题：序列化是否保留 monotonic 信息；不同 clock 的值能否直接混用；精度与单位如何转换。
// 对照观察：Round(0) 或序列化移除 monotonic reading；Equal 比较时间点，`==` 还比较内部表示。
package durations_clocks_and_monotonic_time

import (
	"testing"
	"time"
)

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
