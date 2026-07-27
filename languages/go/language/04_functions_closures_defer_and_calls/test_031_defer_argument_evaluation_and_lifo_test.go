// polyglot-covers: go.defer.argument-evaluation-and-lifo
package functions_test

import (
	"slices"
	"testing"
)

func collectDeferredEvents() (events []int) {
	value := 1
	defer func(captured int) { events = append(events, captured) }(value)
	value = 2
	defer func() { events = append(events, value) }()
	return events
}

func TestDeferredCallsRunLifoAfterReturnValuesAreSet(t *testing.T) {
	if got := collectDeferredEvents(); !slices.Equal(got, []int{2, 1}) {
		t.Fatalf("defer 参数立即求值，调用按 LIFO 执行: %v", got)
	}
}
