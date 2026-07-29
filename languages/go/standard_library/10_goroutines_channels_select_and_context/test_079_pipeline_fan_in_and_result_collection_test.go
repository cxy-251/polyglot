// polyglot-covers: go.concurrency.pipeline-ownership-results-and-errors
package concurrency_test

import (
	"context"
	"errors"
	"slices"
	"sync"
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

func TestFanInClosesOutputAfterAllProducersFinish(t *testing.T) {
	output := make(chan int)
	var producers sync.WaitGroup
	for _, value := range []int{2, 3} {
		producers.Add(1)
		go func() {
			defer producers.Done()
			output <- value * value
		}()
	}
	go func() {
		producers.Wait()
		close(output)
	}()
	results := []int{}
	for result := range output {
		results = append(results, result)
	}
	slices.Sort(results)
	if !slices.Equal(results, []int{4, 9}) {
		t.Fatalf("fan-in 顺序不保证，但关闭协议保证收集完成: %v", results)
	}
}

func TestProducerOwnsCloseAndPropagatesCancellation(t *testing.T) {
	contextValue, cancel := context.WithCancel(context.Background())
	cancel()
	result := <-startTask(contextValue)
	if !errors.Is(result.err, context.Canceled) {
		t.Fatalf("buffered terminal result 避免 worker 因调用方取消而泄漏: %+v", result)
	}
}
