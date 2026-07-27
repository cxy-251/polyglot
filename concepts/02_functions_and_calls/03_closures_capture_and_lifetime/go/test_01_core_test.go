// polyglot-family: functions_and_calls
// polyglot-concept: closures_capture_and_lifetime
// polyglot-related: languages/go/language/
// polyglot-related+: 04_functions_closures_defer_and_calls/test_029_closure_capture_and_lifetime_test.go
//
// 共同问题：闭包捕获值还是变量；被捕获状态能否跨调用存活；循环变量是否共享。
// 对照观察：Go 闭包捕获变量；逃逸变量按需移到堆上，Go 1.22+ range 声明变量每轮独立。
package closures_capture_and_lifetime

import "testing"

func counterClosure() func() int {
	value := 0
	return func() int {
		value++
		return value
	}
}

func TestClosureExtendsCapturedVariableLifetime(t *testing.T) {
	next := counterClosure()
	if next() != 1 || next() != 2 {
		t.Fatal("函数返回后闭包继续共享同一捕获变量")
	}
	callbacks := []func() int{}
	for _, value := range []int{3, 4} {
		callbacks = append(callbacks, func() int { return value })
	}
	if callbacks[0]() != 3 || callbacks[1]() != 4 {
		t.Fatal("当前 Go 版本每轮创建新的 range 声明变量")
	}
}
