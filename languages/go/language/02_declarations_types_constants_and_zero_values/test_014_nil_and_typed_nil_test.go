// polyglot-covers: go.types.nil-and-typed-nil
package declarations_test

import "testing"

type namedError struct{}

func (*namedError) Error() string { return "typed nil" }

func TestInterfaceContainingTypedNilIsNotNil(t *testing.T) {
	var pointer *namedError
	var err error = pointer
	if pointer != nil {
		t.Fatal("指针动态值仍是 nil")
	}
	if err == nil {
		t.Fatal("interface 同时保存动态类型和动态值；只有二者都缺失时才等于 nil")
	}
}
