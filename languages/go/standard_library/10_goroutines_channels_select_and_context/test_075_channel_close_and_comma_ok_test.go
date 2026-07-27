// polyglot-covers: go.channels.close-and-comma-ok
package concurrency_test

import "testing"

func TestClosedChannelDrainsThenReturnsZeroAndFalse(t *testing.T) {
	channel := make(chan int, 1)
	channel <- 3
	close(channel)
	first, firstOK := <-channel
	second, secondOK := <-channel
	if first != 3 || !firstOK || second != 0 || secondOK {
		t.Fatal("close 不丢弃缓冲值；耗尽后 receive 立即返回元素零值与 false")
	}
	// 只有发送方应关闭 channel；向已关闭 channel 发送会 panic。
}
