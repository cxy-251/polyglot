// polyglot-family: objects_and_dispatch
// polyglot-concept: introspection_reflection_and_runtime_type
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_118_reflect_type_value_and_addressability_test.go
//
// 共同问题：运行时能观察哪些类型与成员；反射修改需要什么权限；interface 动态类型如何检查。
// 对照观察：reflect 暴露具体类型和值，但未导出字段和不可寻址值仍受限制；type assertion 更直接。
package introspection_reflection_and_runtime_type

import (
	"reflect"
	"testing"
)

type reflectionRecord struct {
	Name string
}

func TestReflectionSeparatesTypeMetadataFromSettableStorage(t *testing.T) {
	value := reflectionRecord{Name: "go"}
	typeInfo := reflect.TypeOf(value)
	if typeInfo.Name() != "reflectionRecord" || typeInfo.NumField() != 1 {
		t.Fatal("reflect.Type 描述编译后的具体类型结构")
	}
	field := reflect.ValueOf(&value).Elem().FieldByName("Name")
	if !field.CanSet() {
		t.Fatal("pointer Elem 中的导出字段可设置")
	}
	field.SetString("changed")
	if value.Name != "changed" {
		t.Fatal("reflect.Value 写回原存储")
	}
}
