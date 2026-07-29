// polyglot-covers: go.functions.values-method-values-and-expressions
package functions_test

import "testing"

type multiplier struct{ factor int }

func (receiver multiplier) Scale(value int) int { return receiver.factor * value }

func apply(value int, operation func(int) int) int {
	return operation(value)
}

func TestMethodValueBindsReceiverWhileExpressionExposesIt(t *testing.T) {
	item := multiplier{factor: 3}
	bound := item.Scale
	unbound := multiplier.Scale
	item.factor = 9
	if bound(2) != 6 {
		t.Fatal("value receiver 的 method value 在求值时复制并绑定 receiver")
	}
	if unbound(item, 2) != 18 {
		t.Fatal("method expression 把 receiver 变成显式第一个参数")
	}
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
