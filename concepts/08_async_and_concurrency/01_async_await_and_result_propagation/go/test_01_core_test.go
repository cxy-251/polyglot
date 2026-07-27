// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 10_goroutines_channels_select_and_context/test_073_goroutine_start_and_result_channels_test.go
//
// 共同问题：异步工作何时开始；调用方如何等待并取得值或错误；结果能否重复读取。
// 对照观察：Go 没有 async/await；goroutine 启动工作，channel receive 是显式等待与结果传递边界。
package async_await_and_result_propagation

import (
	"errors"
	"testing"
)

type asyncResult struct {
	value int
	err   error
}

func startAsync(success bool) <-chan asyncResult {
	results := make(chan asyncResult, 1)
	go func() {
		defer close(results)
		if !success {
			results <- asyncResult{err: errors.New("failed")}
			return
		}
		results <- asyncResult{value: 42}
	}()
	return results
}

func TestChannelCarriesOneResultAndCompletion(t *testing.T) {
	result := <-startAsync(true)
	if result.value != 42 || result.err != nil {
		t.Fatalf("调用方通过 receive 等待结果: %+v", result)
	}
}
