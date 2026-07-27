// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 11_sync_atomic_and_memory_model/test_088_happens_before_and_publication_test.go
//
// 共同问题：并发任务映射到线程还是进程；共享哪些内存；隔离边界由谁提供。
// 对照观察：goroutine 由 runtime 多路复用到 OS threads，并共享 Go heap；它不是 worker/process 隔离。
package threads_workers_and_process_isolation

import (
	"runtime"
	"testing"
)

func TestGoroutinesShareHeapAndSchedulerChoosesThreads(t *testing.T) {
	shared := make(chan *int, 1)
	value := 7
	go func() { shared <- &value }()
	pointer := <-shared
	*pointer = 9
	if value != 9 || runtime.GOMAXPROCS(0) < 1 {
		t.Fatal("goroutine 可传递同一 heap 对象；GOMAXPROCS 只限制并行执行资源")
	}
	runtime.LockOSThread()
	runtime.UnlockOSThread()
	// LockOSThread 只用于线程亲和 API，不把 goroutine 变成内存隔离 worker。
}
