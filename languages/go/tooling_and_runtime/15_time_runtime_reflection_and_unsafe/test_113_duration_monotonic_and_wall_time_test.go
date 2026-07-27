// polyglot-covers: go.time.duration-monotonic-wall
package runtimeintrospection_test

import (
	"testing"
	"time"
)

func TestDurationIsNanosecondsAndMonotonicDataIsProcessLocal(t *testing.T) {
	duration := 2*time.Second + 250*time.Millisecond
	if duration.Milliseconds() != 2250 {
		t.Fatal("Duration 是 int64 纳秒计数，单位常量让表达式保持可读")
	}
	now := time.Now()
	wallOnly := now.Round(0)
	if !now.Equal(wallOnly) || now == wallOnly {
		t.Fatal("Equal 比较时间点；== 还比较 location 与不可序列化的 monotonic reading")
	}
}
