// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_076_nil_channels_and_select_default_test.go
//
// 共同问题：多个已就绪任务的优先级是什么；队列边界能否依赖固定先后。
// 对照观察：select 在多个就绪 case 中伪随机选择；程序必须对任一合法分支都正确。
package scheduling_tasks_microtasks_and_futures

import "testing"

func TestSelectDoesNotPrioritizeSourceOrder(t *testing.T) {
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
	// 公平性不等于可预测顺序；测试不应统计某次运行的选择比例。
}
