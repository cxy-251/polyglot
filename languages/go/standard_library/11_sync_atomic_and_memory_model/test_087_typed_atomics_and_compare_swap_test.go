// polyglot-covers: go.memory-model.atomics-happens-before-and-publication
package synchronization_test

import (
	"sync/atomic"
	"testing"
)

type publishedConfig struct {
	name string
	port int
}

func TestCompareAndSwapChangesOnlyExpectedState(t *testing.T) {
	var state atomic.Int64
	state.Store(1)
	if state.CompareAndSwap(0, 2) {
		t.Fatal("CAS 在旧值不匹配时不写入")
	}
	if !state.CompareAndSwap(1, 2) || state.Load() != 2 {
		t.Fatal("typed atomic API 使单一变量的原子状态转换可读")
	}
	// 多字段 invariant 仍需要 mutex 或消息传递，不能由多个独立 atomic 自动组成事务。
}

func TestChannelSendPublishesEarlierWrites(t *testing.T) {
	channel := make(chan *publishedConfig)
	go func() {
		config := &publishedConfig{name: "service", port: 8080}
		channel <- config
	}()
	config := <-channel
	if config.name != "service" || config.port != 8080 {
		t.Fatal("对应 send/receive 建立 happens-before，receiver 可见发送前写入")
	}
	// 发布后保持对象不可变；无同步并发读写同一字段仍是 data race。
}
