// polyglot-covers: go.functions.values-and-higher-order
package functions_test

import "testing"

func apply(value int, operation func(int) int) int {
	return operation(value)
}

func TestFunctionsAreValuesButOnlyComparableToNil(t *testing.T) {
	double := func(value int) int { return value * 2 }
	if apply(5, double) != 10 {
		t.Fatal("函数值可作为参数和返回值")
	}
	var absent func(int) int
	if absent != nil {
		t.Fatal("函数零值是 nil；非 nil 函数之间不可比较")
	}
}
