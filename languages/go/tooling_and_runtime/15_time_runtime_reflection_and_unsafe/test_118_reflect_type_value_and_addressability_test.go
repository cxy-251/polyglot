// polyglot-covers: go.reflect.type-value-addressability
package runtimeintrospection_test

import (
	"reflect"
	"testing"
)

func TestReflectionMutationRequiresAddressableSettableValue(t *testing.T) {
	number := 7
	direct := reflect.ValueOf(number)
	if direct.CanAddr() || direct.CanSet() {
		t.Fatal("装箱的值副本不可寻址、不可设置")
	}
	target := reflect.ValueOf(&number).Elem()
	if !target.CanAddr() || !target.CanSet() || target.Type().Kind() != reflect.Int {
		t.Fatal("pointer Elem 暴露可寻址、可设置的原存储")
	}
	target.SetInt(9)
	if number != 9 {
		t.Fatal("SetInt 修改反射值指向的原变量")
	}
}
