// polyglot-covers: go.functions.closure-capture-and-lifetime
package functions_test

import "testing"

func TestClosureCapturesVariablesNotSnapshots(t *testing.T) {
	counter := 0
	next := func() int {
		counter++
		return counter
	}
	if next() != 1 || next() != 2 {
		t.Fatal("闭包延长被捕获变量的生命周期并共享同一存储")
	}
	callbacks := []func() int{}
	for _, value := range []int{3, 4} {
		callbacks = append(callbacks, func() int { return value })
	}
	if callbacks[0]() != 3 || callbacks[1]() != 4 {
		t.Fatal("Go 1.22+ range 声明变量每轮独立，闭包不会都看到最后一个值")
	}
}
