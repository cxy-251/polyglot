// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_060_panic_and_recover_position_test.go
//
// 共同问题：重新传播是否保留原失败；清理期间再次失败时哪个 completion 胜出。
// 对照观察：recover 后 `panic(value)` 可重抛；panic 展开期间新的 panic 会替代正在传播的值。
package exception_propagation_and_matching

import "testing"

func replacementPanic() (recovered any) {
	defer func() { recovered = recover() }()
	func() {
		defer func() { panic("cleanup") }()
		panic("original")
	}()
	return nil
}

func TestPanicDuringUnwindReplacesOriginalPanic(t *testing.T) {
	if replacementPanic() != "cleanup" {
		t.Fatal("defer 中的新 panic 成为当前传播值；需要保留两者时必须自行包装")
	}
}
