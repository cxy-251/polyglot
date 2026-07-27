// polyglot-family: functions_and_calls
// polyglot-concept: callable_adaptation_and_partial_application
// polyglot-related: languages/go/language/
// polyglot-related+: 04_functions_closures_defer_and_calls/test_028_function_values_and_higher_order_calls_test.go
//
// 共同问题：如何把现有 callable 调整为另一调用签名；部分参数怎样稳定绑定。
// 对照观察：Go 没有通用 bind 内建，通常用类型安全闭包或 method value 显式适配。
package callable_adaptation_and_partial_application

import "testing"

func bindLeft[A, B, R any](function func(A, B) R, left A) func(B) R {
	return func(right B) R { return function(left, right) }
}

func TestClosureProvidesTypedPartialApplication(t *testing.T) {
	add := func(left, right int) int { return left + right }
	addTen := bindLeft(add, 10)
	if addTen(5) != 15 {
		t.Fatal("闭包保存已绑定参数，泛型保持剩余调用签名")
	}
}
