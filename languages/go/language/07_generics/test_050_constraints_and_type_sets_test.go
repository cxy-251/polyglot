// polyglot-covers: go.generics.constraints-and-type-sets
package generics_test

import "testing"

type signedInteger interface {
	~int | ~int32 | ~int64
}

func genericSum[T signedInteger](values []T) T {
	var total T
	for _, value := range values {
		total += value
	}
	return total
}

func TestConstraintPermitsOnlyItsTypeSetOperations(t *testing.T) {
	if genericSum([]int32{1, 2, 3}) != 6 {
		t.Fatal("constraint 的 type set 决定可实例化类型及函数体可用操作")
	}
}
