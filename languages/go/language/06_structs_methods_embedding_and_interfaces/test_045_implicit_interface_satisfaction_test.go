// polyglot-covers: go.interfaces.implicit-satisfaction-values-and-typed-nil
package objects_test

import "testing"

type speaker interface {
	Speak() string
}

type quietSpeaker struct{}

func (quietSpeaker) Speak() string { return "hello" }

type nilAware struct{}

func (*nilAware) Ready() bool { return false }

type readiness interface {
	Ready() bool
}

func TestInterfaceImplementationNeedsNoDeclaration(t *testing.T) {
	var value speaker = quietSpeaker{}
	if value.Speak() != "hello" {
		t.Fatal("method set 满足 interface 即隐式实现，调用按动态类型分派")
	}
	var _ speaker = quietSpeaker{}
	// 编译期赋值断言可记录意图，但不是实现 interface 所必需。
}

func TestInterfaceKeepsDynamicTypeForNilPointer(t *testing.T) {
	var pointer *nilAware
	var value readiness = pointer
	if value == nil || value.Ready() {
		t.Fatal("interface 保存 (*nilAware, nil)，所以自身非 nil 且仍可动态分派")
	}
}
