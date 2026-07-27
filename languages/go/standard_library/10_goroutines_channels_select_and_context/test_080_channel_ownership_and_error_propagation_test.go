// polyglot-covers: go.concurrency.ownership-errors-leak-prevention
package concurrency_test

import (
	"context"
	"errors"
	"testing"
)

type taskResult struct {
	value int
	err   error
}

func startTask(contextValue context.Context) <-chan taskResult {
	results := make(chan taskResult, 1)
	go func() {
		defer close(results)
		if err := contextValue.Err(); err != nil {
			results <- taskResult{err: err}
			return
		}
		select {
		case <-contextValue.Done():
			results <- taskResult{err: contextValue.Err()}
		case results <- taskResult{value: 42}:
		}
	}()
	return results
}

func TestProducerOwnsCloseAndPropagatesCancellation(t *testing.T) {
	contextValue, cancel := context.WithCancel(context.Background())
	cancel()
	result := <-startTask(contextValue)
	if !errors.Is(result.err, context.Canceled) {
		t.Fatalf("buffered terminal result 避免 worker 因调用方取消而泄漏: %+v", result)
	}
}
