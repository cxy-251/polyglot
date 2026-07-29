// polyglot-covers: go.time.duration-monotonic-and-timer-lifecycles
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

func TestTimersAndTickersRequireExplicitLifecycle(t *testing.T) {
	timer := time.NewTimer(time.Hour)
	if !timer.Stop() {
		t.Fatal("尚未触发的 timer 应可停止")
	}
	ticker := time.NewTicker(time.Hour)
	ticker.Stop()
	select {
	case <-ticker.C:
		t.Fatal("长周期 ticker 停止后不应已有 tick")
	default:
	}
	// Stop 不关闭 ticker.C；等待 channel close 会永久阻塞，所有者应通过独立取消协议退出。
}
