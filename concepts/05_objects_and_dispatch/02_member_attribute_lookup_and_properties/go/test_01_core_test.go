// polyglot-family: objects_and_dispatch
// polyglot-concept: member_attribute_lookup_and_properties
// polyglot-related: languages/go/language/
// polyglot-related+: 06_structs_methods_embedding_and_interfaces/test_041_struct_values_and_layout_boundary_test.go
//
// 共同问题：成员名称如何解析；读取或赋值能否触发用户代码；缺失成员怎样失败。
// 对照观察：Go selector 在编译期解析字段与 method，embedding 可提升名称；语言没有动态 property hook。
package member_attribute_lookup_and_properties

import "testing"

type profile struct{ name string }

func (value profile) Name() string { return value.name }
func (value *profile) Rename(name string) {
	value.name = name
}

func TestMethodsProvideExplicitPropertyLikeAPI(t *testing.T) {
	value := profile{name: "before"}
	if value.Name() != "before" {
		t.Fatal("getter 是普通方法调用，不是字段访问时的隐式 hook")
	}
	value.Rename("after")
	if value.Name() != "after" {
		t.Fatal("pointer receiver setter 明确执行验证或更新逻辑")
	}
	// 不存在的 selector 是编译期错误，不会回退到 __getattr__ 或 Proxy。
}
