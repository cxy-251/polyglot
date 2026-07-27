// polyglot-covers: go.concurrency.goroutine-start-result
package concurrency_test

import "testing"

func TestCallerWaitsForGoroutineThroughAResultChannel(t *testing.T) {
	started := make(chan struct{})
	result := make(chan int, 1)
	go func() {
		close(started)
		result <- 6 * 7
	}()
	<-started
	if value := <-result; value != 42 {
		t.Fatalf("goroutine 独立调度；channel 明确传回结果和等待边界: %d", value)
	}
}
