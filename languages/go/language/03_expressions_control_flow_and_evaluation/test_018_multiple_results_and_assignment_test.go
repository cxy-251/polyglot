// polyglot-covers: go.expressions.multiple-results-and-assignment
package controlflow_test

import "testing"

func quotientAndRemainder(value, divisor int) (int, int) {
	return value / divisor, value % divisor
}

func TestParallelAssignmentUsesOldOperands(t *testing.T) {
	left, right := 1, 2
	left, right = right, left
	quotient, remainder := quotientAndRemainder(11, 4)
	if left != 2 || right != 1 || quotient != 2 || remainder != 3 {
		t.Fatal("多重赋值先求右侧，再向各左值赋值")
	}
}
