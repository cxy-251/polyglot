// polyglot-covers: go.sync.once-pool-and-concurrent-map-lifecycles
package synchronization_test

import (
	"bytes"
	"sync"
	"testing"
)

func TestOnceValuePublishesOneComputedResult(t *testing.T) {
	calls := 0
	load := sync.OnceValue(func() int {
		calls++
		return 42
	})
	if load() != 42 || load() != 42 || calls != 1 {
		t.Fatal("OnceValue 只执行一次函数，并把同一结果安全发布给后续调用")
	}
	// 若初始化函数 panic，Once/OnceValue 会把该次调用视为已发生，不能当重试器使用。
}

func TestPoolReusesScratchValuesWithoutRetentionGuarantee(t *testing.T) {
	pool := sync.Pool{New: func() any { return new(bytes.Buffer) }}
	buffer := pool.Get().(*bytes.Buffer)
	buffer.WriteString("temporary")
	buffer.Reset()
	pool.Put(buffer)
	reused := pool.Get().(*bytes.Buffer)
	if reused.Len() != 0 {
		t.Fatal("归还前必须恢复对象状态；GC 可随时丢弃 pool 条目")
	}

	var values sync.Map
	values.Store("key", 7)
	if value, ok := values.Load("key"); !ok || value != 7 {
		t.Fatal("sync.Map 为特定共享访问模式提供并发安全操作")
	}
}
