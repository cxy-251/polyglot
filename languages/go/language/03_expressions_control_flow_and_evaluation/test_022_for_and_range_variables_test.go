// polyglot-covers: go.statements.for-range-variables
package controlflow_test

import "testing"

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
