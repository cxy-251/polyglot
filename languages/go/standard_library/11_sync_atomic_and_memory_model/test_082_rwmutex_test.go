// polyglot-covers: go.sync.rwmutex
package synchronization_test

import (
	"sync"
	"testing"
)

func TestRWMutexProtectsSharedReadAndWriteAccess(t *testing.T) {
	var mutex sync.RWMutex
	value := 1
	read := func() int {
		mutex.RLock()
		defer mutex.RUnlock()
		return value
	}
	mutex.Lock()
	value = 2
	mutex.Unlock()
	if read() != 2 {
		t.Fatal("读写双方必须使用同一 RWMutex 才构成同步关系")
	}
}
