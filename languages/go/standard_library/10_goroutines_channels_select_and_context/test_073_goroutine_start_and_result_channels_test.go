// polyglot-covers: go.channels.goroutine-results-buffering-and-synchronization
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

func TestUnbufferedSendSynchronizesWithReceiver(t *testing.T) {
	channel := make(chan int)
	ready := make(chan struct{})
	sent := make(chan struct{})
	go func() {
		close(ready)
		channel <- 7
		close(sent)
	}()
	<-ready
	select {
	case <-sent:
		t.Fatal("无缓冲 send 必须等待对应 receive")
	default:
	}
	if <-channel != 7 {
		t.Fatal("receiver 取得发送值")
	}
	<-sent

	buffered := make(chan int, 1)
	buffered <- 9
	if <-buffered != 9 {
		t.Fatal("有空位的 buffered channel 可在没有同步 receiver 时保存值")
	}
}
