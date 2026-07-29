// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_073_goroutine_start_and_result_channels_test.go
//
// 共同问题：新任务何时获得执行机会；同步代码与已就绪 continuation 采用什么顺序。
// 对照观察：Go scheduler 不承诺 goroutine 在下一条语句前运行，也没有 JavaScript microtask queue。
package scheduling_tasks_microtasks_and_futures

import (
	"slices"
	"testing"
)

func TestSynchronizationNotSourceOrderDefinesCrossGoroutineOrder(t *testing.T) {
	events := []string{"caller:start"}
	started := make(chan struct{})
	done := make(chan struct{})
	go func() {
		close(started)
		events = append(events, "worker")
		close(done)
	}()
	<-started
	<-done
	events = append(events, "caller:end")
	if !slices.Equal(events, []string{"caller:start", "worker", "caller:end"}) {
		t.Fatalf("channel 建立观察顺序；单凭 go statement 后的源码顺序不建立保证: %v", events)
	}
}

func TestSelectAllowsAnyReadyCase(t *testing.T) {
	first := make(chan int, 1)
	second := make(chan int, 1)
	first <- 1
	second <- 2
	selected := 0
	select {
	case selected = <-first:
	case selected = <-second:
	}
	if selected != 1 && selected != 2 {
		t.Fatalf("两个 case 均已就绪，任一都合法: %d", selected)
	}
	// 规范从可继续执行的 case 中伪随机选择一个；单次测试不证明长期公平性或实现分布。
}
