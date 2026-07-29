// polyglot-covers: go.context.cancellation-deadlines-and-values
package concurrency_test

import (
	"context"
	"errors"
	"testing"
	"time"
)

type requestKey struct{}

func TestWorkerObservesContextCancellationWithoutPolling(t *testing.T) {
	contextValue, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		select {
		case <-contextValue.Done():
			done <- contextValue.Err()
		}
	}()
	cancel()
	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("Done channel 建立明确取消事件: %v", err)
	}
}

func TestExpiredDeadlineAndRequestScopedValue(t *testing.T) {
	parent := context.WithValue(context.Background(), requestKey{}, "request-7")
	expired, cancel := context.WithDeadline(parent, time.Unix(0, 0))
	defer cancel()
	<-expired.Done()
	if !errors.Is(expired.Err(), context.DeadlineExceeded) ||
		expired.Value(requestKey{}) != "request-7" {
		t.Fatal("deadline 关闭 Done；派生 context 仍沿父链查询 request-scoped value")
	}
	// context value 只携带跨 API 边界的请求数据，不替代普通函数参数。
}
