// polyglot-covers: go.generics.constraints-unions-and-approximation
package generics_test

import "testing"

type signedInteger interface {
	~int | ~int32 | ~int64
}

type distance int

type addable interface {
	~int | ~string
}

func addValues[T addable](left, right T) T { return left + right }

func genericSum[T signedInteger](values []T) T {
	var total T
	for _, value := range values {
		total += value
	}
	return total
}

func TestTildeIncludesDefinedTypesWithMatchingUnderlyingType(t *testing.T) {
	if addValues(distance(2), distance(3)) != 5 || addValues("go", "pher") != "gopher" {
		t.Fatal("~int 包含底层类型为 int 的 defined type；union 合并允许的 type terms")
	}
}

func TestConstraintPermitsOnlyItsTypeSetOperations(t *testing.T) {
	if genericSum([]int32{1, 2, 3}) != 6 {
		t.Fatal("constraint 的 type set 决定可实例化类型及函数体可用操作")
	}
}
