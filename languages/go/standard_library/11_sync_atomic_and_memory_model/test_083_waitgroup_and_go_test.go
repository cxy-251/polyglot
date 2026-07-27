// polyglot-covers: go.sync.waitgroup
package synchronization_test

import (
	"sync"
	"sync/atomic"
	"testing"
)

func TestWaitGroupTracksASetOfTasks(t *testing.T) {
	var group sync.WaitGroup
	var completed atomic.Int64
	for range 4 {
		group.Go(func() {
			completed.Add(1)
		})
	}
	group.Wait()
	if completed.Load() != 4 {
		t.Fatal("Go 1.25+ WaitGroup.Go 将 Add、启动和 Done 组合为安全任务入口")
	}
	// 传统 Add/Done 仍适用于需要把任务计数与 goroutine 启动分开的协议。
}
