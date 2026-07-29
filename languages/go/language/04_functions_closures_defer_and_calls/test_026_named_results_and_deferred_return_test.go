// polyglot-covers: go.defer.arguments-order-and-named-results
package functions_test

import (
	"slices"
	"testing"
)

func incrementOnReturn() (result int) {
	result = 4
	defer func() { result++ }()
	return
}

func collectDeferredEvents() (events []int) {
	value := 1
	defer func(captured int) { events = append(events, captured) }(value)
	value = 2
	defer func() { events = append(events, value) }()
	return events
}

func TestDeferredFunctionCanObserveNamedResult(t *testing.T) {
	if incrementOnReturn() != 5 {
		t.Fatal("return 先写入命名结果，随后 defer 可在函数真正返回前修改它")
	}
	// 过度依赖命名结果的隐式修改会降低可读性，应只用于清晰的收尾语义。
}

func TestDeferredCallsRunLifoAfterReturnValuesAreSet(t *testing.T) {
	if got := collectDeferredEvents(); !slices.Equal(got, []int{2, 1}) {
		t.Fatalf("defer 参数立即求值，调用按 LIFO 执行: %v", got)
	}
}
