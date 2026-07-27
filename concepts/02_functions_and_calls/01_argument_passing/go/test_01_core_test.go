// polyglot-family: functions_and_calls
// polyglot-concept: argument_passing
// polyglot-related: languages/go/language/
// polyglot-related+: 04_functions_closures_defer_and_calls/test_025_parameters_are_passed_by_value_test.go
//
// 共同问题：参数传递复制绑定还是对象；函数内修改何时能被调用方观察。
// 对照观察：Go 所有参数按值复制；复制的 slice、map、channel 或 pointer 仍可能共享底层状态。
package argument_passing

import "testing"

func mutateArguments(number int, values []int, mapping map[string]int) {
	number = 9
	values[0] = 9
	mapping["value"] = 9
}

func TestParameterVariablesAreCopiesWithPossibleSharedReferents(t *testing.T) {
	number := 1
	values := []int{1}
	mapping := map[string]int{"value": 1}
	mutateArguments(number, values, mapping)
	if number != 1 || values[0] != 9 || mapping["value"] != 9 {
		t.Fatal("重绑 int 形参不回写；slice/map 副本仍访问共享内容")
	}
}
