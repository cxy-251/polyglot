// polyglot-covers: go.channels.nil-and-select-default
package concurrency_test

import "testing"

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
