// polyglot-covers: go.concurrency.select-and-cancellation
package concurrency_test

import (
	"context"
	"errors"
	"testing"
)

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
