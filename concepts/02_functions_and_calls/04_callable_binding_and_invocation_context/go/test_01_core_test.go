// polyglot-family: functions_and_calls
// polyglot-concept: callable_binding_and_invocation_context
// polyglot-related: languages/go/language/
// polyglot-related+: 04_functions_closures_defer_and_calls/test_028_function_values_and_higher_order_calls_test.go
//
// 共同问题：可调用值是否绑定接收者；提取方法后调用上下文如何决定。
// 对照观察：Go method value 绑定 receiver，method expression 则把 receiver 变成显式首参。
package callable_binding_and_invocation_context

import "testing"

type callableScale struct{ factor int }

func (value callableScale) Apply(number int) int { return value.factor * number }

func TestMethodValueAndExpressionExposeDifferentCallShapes(t *testing.T) {
	value := callableScale{factor: 2}
	bound := value.Apply
	expression := callableScale.Apply
	value.factor = 3
	if bound(4) != 8 || expression(value, 4) != 12 {
		t.Fatal("value receiver 的 method value 捕获求值时副本；expression 由调用者传 receiver")
	}
}
