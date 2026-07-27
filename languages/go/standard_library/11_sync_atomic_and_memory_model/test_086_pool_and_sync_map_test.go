// polyglot-covers: go.sync.pool-and-map
package synchronization_test

import (
	"bytes"
	"sync"
	"testing"
)

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
