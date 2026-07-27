// polyglot-covers: go.sync.mutex-and-lost-updates
package synchronization_test

import (
	"sync"
	"testing"
)

func TestMutexSerializesReadModifyWrite(t *testing.T) {
	var mutex sync.Mutex
	counter := 0
	var workers sync.WaitGroup
	for range 100 {
		workers.Add(1)
		go func() {
			defer workers.Done()
			mutex.Lock()
			counter++
			mutex.Unlock()
		}()
	}
	workers.Wait()
	if counter != 100 {
		t.Fatalf("复合增量必须作为一个临界区，避免 lost update: %d", counter)
	}
}
