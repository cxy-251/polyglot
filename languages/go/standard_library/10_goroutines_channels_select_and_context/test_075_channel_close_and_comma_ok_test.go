// polyglot-covers: go.channels.closed-nil-and-select-boundaries
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

func TestNilChannelCaseIsDisabledInsideSelect(t *testing.T) {
	var disabled <-chan int
	selected := ""
	select {
	case <-disabled:
		selected = "nil channel"
	default:
		selected = "default"
	}
	if selected != "default" {
		t.Fatal("nil channel 单独收发会永久阻塞，在 select 中对应 case 永不就绪")
	}
}
