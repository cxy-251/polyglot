// polyglot-covers: go.sync.once-and-once-value
package synchronization_test

import (
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
