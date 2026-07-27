// polyglot-covers: go.time.timers-and-tickers
package runtimeintrospection_test

import (
	"testing"
	"time"
)

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
