// polyglot-covers: go.concurrency.pipeline-fan-in-results
package concurrency_test

import (
	"slices"
	"sync"
	"testing"
)

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
