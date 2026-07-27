// polyglot-covers: go.interfaces.values-and-typed-nil
package objects_test

import "testing"

type nilAware struct{}

func (*nilAware) Ready() bool { return false }

type readiness interface {
	Ready() bool
}

func TestInterfaceKeepsDynamicTypeForNilPointer(t *testing.T) {
	var pointer *nilAware
	var value readiness = pointer
	if value == nil || value.Ready() {
		t.Fatal("interface 保存 (*nilAware, nil)，所以自身非 nil 且仍可动态分派")
	}
}
