// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_077_select_and_explicit_cancellation_test.go
//
// 共同问题：timeout 资源由谁释放；子任务能否与父取消隔离；取消原因如何保留。
// 对照观察：创建 deadline 的调用方应调用 cancel；WithoutCancel 可屏蔽父取消，但也移除 Done/deadline。
package cancellation_timeouts_and_cleanup

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestCancelCauseAndWithoutCancelExposeOwnershipChoices(t *testing.T) {
	cause := errors.New("owner stopped")
	parent, cancelCause := context.WithCancelCause(context.Background())
	cancelCause(cause)
	if !errors.Is(context.Cause(parent), cause) {
		t.Fatal("WithCancelCause 保留机器可读取消原因")
	}
	shielded := context.WithoutCancel(parent)
	if shielded.Err() != nil || shielded.Done() != nil {
		t.Fatal("WithoutCancel 不继承父取消；调用方必须另建终止边界")
	}
	timed, cancel := context.WithTimeout(shielded, time.Hour)
	cancel()
	if !errors.Is(timed.Err(), context.Canceled) {
		t.Fatal("创建 timeout 的所有者仍应 cancel，及时释放 timer 资源")
	}
}
