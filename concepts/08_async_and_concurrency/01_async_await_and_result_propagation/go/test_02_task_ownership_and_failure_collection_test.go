// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_079_pipeline_fan_in_and_result_collection_test.go
//
// 共同问题：多个任务由谁等待；失败是否被遗漏；结果收集何时结束。
// 对照观察：Go 没有自动 task tree；所有者用 WaitGroup、channel close 和显式 error 聚合建立生命周期。
package async_await_and_result_propagation

import (
	"errors"
	"sync"
	"testing"
)

func TestOwnerWaitsAndCollectsEveryFailure(t *testing.T) {
	errorsChannel := make(chan error, 2)
	var group sync.WaitGroup
	for _, label := range []string{"first", "second"} {
		group.Go(func() { errorsChannel <- errors.New(label) })
	}
	go func() {
		group.Wait()
		close(errorsChannel)
	}()
	collected := []error{}
	for err := range errorsChannel {
		collected = append(collected, err)
	}
	combined := errors.Join(collected...)
	if combined == nil || len(collected) != 2 {
		t.Fatal("关闭 output 的协调者必须等待全部 producer，避免静默丢失失败")
	}
}
