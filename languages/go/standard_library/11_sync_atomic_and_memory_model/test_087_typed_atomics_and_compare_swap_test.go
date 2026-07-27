// polyglot-covers: go.atomic.typed-api-and-cas
package synchronization_test

import (
	"sync/atomic"
	"testing"
)

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
