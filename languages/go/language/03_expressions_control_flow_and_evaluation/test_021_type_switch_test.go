// polyglot-covers: go.control.type-switch-and-range
package controlflow_test

import "testing"

func describeDynamicValue(value any) string {
	switch typed := value.(type) {
	case nil:
		return "nil"
	case int:
		return "int"
	case string:
		return "string:" + typed
	default:
		return "other"
	}
}

func TestRangeCopiesElementsAndCreatesIterationVariables(t *testing.T) {
	values := []int{10, 20, 30}
	pointers := []*int{}
	for _, value := range values {
		value++
		pointers = append(pointers, &value)
	}
	if values[0] != 10 || *pointers[0] != 11 || *pointers[1] != 21 {
		t.Fatal("range value 是元素副本；Go 1.22+ 声明式迭代变量每轮重新创建")
	}
	count := 0
	for range 3 {
		count++
	}
	if count != 3 {
		t.Fatal("range 整数执行从 0 到 n-1 的迭代次数")
	}
}

func TestTypeSwitchMatchesInterfaceDynamicType(t *testing.T) {
	if describeDynamicValue(nil) != "nil" ||
		describeDynamicValue(3) != "int" ||
		describeDynamicValue("go") != "string:go" {
		t.Fatal("type switch 按 interface 的动态类型选择分支")
	}
}
