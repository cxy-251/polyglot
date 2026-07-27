// polyglot-covers: go.sync.cond-predicate-loop
package synchronization_test

import (
	"sync"
	"testing"
)

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
