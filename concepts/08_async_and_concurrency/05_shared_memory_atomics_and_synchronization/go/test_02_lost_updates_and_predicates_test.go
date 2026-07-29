// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 11_sync_atomic_and_memory_model/test_083_waitgroup_and_go_test.go
//
// 共同问题：read-modify-write 怎样丢更新；条件通知能否代替状态 predicate。
// 对照观察：Go mutex 必须覆盖整个复合操作；Cond 的 Signal 只是提示，等待方始终循环检查 predicate。
package shared_memory_atomics_and_synchronization

import (
	"sync"
	"testing"
)

func TestStaleReadsExplainLostUpdateAndCondUsesPredicate(t *testing.T) {
	counter := 0
	firstRead, secondRead := counter, counter
	counter = firstRead + 1
	counter = secondRead + 1
	if counter != 1 {
		t.Fatal("两个 stale read 后的写入会覆盖一次更新")
	}

	condition := sync.NewCond(&sync.Mutex{})
	ready := false
	done := make(chan struct{})
	go func() {
		condition.L.Lock()
		for !ready {
			condition.Wait()
		}
		condition.L.Unlock()
		close(done)
	}()
	condition.L.Lock()
	ready = true
	condition.Signal()
	condition.L.Unlock()
	<-done
}
