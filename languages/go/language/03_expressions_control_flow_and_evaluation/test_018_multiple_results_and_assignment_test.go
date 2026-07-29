// polyglot-covers: go.expressions.assignment-and-evaluation-order
package controlflow_test

import (
	"slices"
	"testing"
)

func quotientAndRemainder(value, divisor int) (int, int) {
	return value / divisor, value % divisor
}

func TestCallsAreEvaluatedInLexicalLeftToRightOrder(t *testing.T) {
	events := []string{}
	observe := func(label string, value int) int {
		events = append(events, label)
		return value
	}
	result := observe("left", 1) + observe("middle", 2)*observe("right", 3)
	if result != 7 || !slices.Equal(events, []string{"left", "middle", "right"}) {
		t.Fatalf("函数调用按词法从左到右求值: result=%d events=%v", result, events)
	}
	// 不含调用的独立子表达式可能没有额外顺序保证，不应借此构造副作用依赖。
}

func TestParallelAssignmentUsesOldOperands(t *testing.T) {
	left, right := 1, 2
	left, right = right, left
	quotient, remainder := quotientAndRemainder(11, 4)
	if left != 2 || right != 1 || quotient != 2 || remainder != 3 {
		t.Fatal("多重赋值先求右侧，再向各左值赋值")
	}
}
