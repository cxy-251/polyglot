// polyglot-covers: go.memory-model.happens-before-publication
package synchronization_test

import "testing"

type publishedConfig struct {
	name string
	port int
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
