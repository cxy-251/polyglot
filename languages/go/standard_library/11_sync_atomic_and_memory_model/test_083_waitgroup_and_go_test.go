// polyglot-covers: go.sync.waitgroup-cond-and-predicates
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

func TestCondWaitAlwaysRechecksPredicate(t *testing.T) {
	condition := sync.NewCond(&sync.Mutex{})
	ready := false
	started := make(chan struct{})
	done := make(chan struct{})
	go func() {
		condition.L.Lock()
		close(started)
		for !ready {
			condition.Wait()
		}
		condition.L.Unlock()
		close(done)
	}()
	<-started
	condition.L.Lock()
	ready = true
	condition.Signal()
	condition.L.Unlock()
	<-done
	// Signal 只是唤醒提示；predicate 才是状态，因此 Wait 必须放在循环中。
}
