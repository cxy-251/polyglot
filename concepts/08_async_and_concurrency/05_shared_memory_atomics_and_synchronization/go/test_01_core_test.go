// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 11_sync_atomic_and_memory_model/test_087_typed_atomics_and_compare_swap_test.go
//
// 共同问题：共享读写如何同步；atomic、lock 与消息传递分别保证什么。
// 对照观察：Go data race 是程序错误；sync/atomic 处理单值原子状态，mutex 或 channel 维护复合 invariant。
package shared_memory_atomics_and_synchronization

import (
	"sync"
	"sync/atomic"
	"testing"
)

func TestAtomicCounterAndMutexProtectedState(t *testing.T) {
	var counter atomic.Int64
	var mutex sync.Mutex
	values := []int{}
	var group sync.WaitGroup
	for value := range 4 {
		group.Go(func() {
			counter.Add(1)
			mutex.Lock()
			values = append(values, value)
			mutex.Unlock()
		})
	}
	group.Wait()
	if counter.Load() != 4 || len(values) != 4 {
		t.Fatal("atomic 保证计数更新；slice 的复合结构修改由 mutex 保护")
	}
}
