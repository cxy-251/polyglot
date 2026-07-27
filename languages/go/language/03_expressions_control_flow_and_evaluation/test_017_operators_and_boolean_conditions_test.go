// polyglot-covers: go.expressions.operators-and-bool-conditions
package controlflow_test

import "testing"

func TestOperatorsPreserveTypedSemantics(t *testing.T) {
	if 7/2 != 3 || 7%2 != 1 {
		t.Fatal("整数除法截向零，并可用余数观察未整除部分")
	}
	if 1<<3|2 != 10 {
		t.Fatal("移位与位运算遵循固定优先级")
	}
	condition := true
	if !condition {
		t.Fatal("if 条件必须具有 bool 类型；数字和容器没有隐式真假转换")
	}
}
