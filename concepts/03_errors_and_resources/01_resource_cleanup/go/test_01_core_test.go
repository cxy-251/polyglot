// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_061_deferred_cleanup_order_test.go
//
// 共同问题：正常或异常离开作用域是否清理；多个资源按什么顺序释放；机制由什么触发。
// 对照观察：Go 在函数返回或 panic 展开时执行 defer；它绑定函数调用，不绑定任意代码块。
package resource_cleanup

import (
	"slices"
	"testing"
)

func cleanupOnReturn() (events []string) {
	defer func() { events = append(events, "first") }()
	defer func() { events = append(events, "second") }()
	return
}

func cleanupOnPanic() (events []string) {
	defer func() {
		events = append(events, "recover")
		_ = recover()
	}()
	defer func() { events = append(events, "resource") }()
	panic("failure")
}

func TestDeferRunsForReturnAndPanicInLifoOrder(t *testing.T) {
	if !slices.Equal(cleanupOnReturn(), []string{"second", "first"}) ||
		!slices.Equal(cleanupOnPanic(), []string{"resource", "recover"}) {
		t.Fatal("defer 在两种退出路径均按后进先出执行")
	}
}
