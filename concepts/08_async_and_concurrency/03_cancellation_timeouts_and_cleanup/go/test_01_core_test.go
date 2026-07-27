// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_077_select_and_explicit_cancellation_test.go
//
// 共同问题：取消如何传递；阻塞工作怎样退出；取消路径是否仍执行清理。
// 对照观察：Go context 是协作式信号，函数必须 select Done；defer 负责 goroutine 内清理。
package cancellation_timeouts_and_cleanup

import (
	"context"
	"errors"
	"testing"
)

func TestCanceledWorkerRunsDeferredCleanup(t *testing.T) {
	contextValue, cancel := context.WithCancel(context.Background())
	events := make(chan string, 1)
	result := make(chan error, 1)
	go func() {
		defer func() { events <- "cleanup" }()
		<-contextValue.Done()
		result <- contextValue.Err()
	}()
	cancel()
	if !errors.Is(<-result, context.Canceled) || <-events != "cleanup" {
		t.Fatal("worker 显式观察 Done，并在返回路径执行 defer")
	}
}
