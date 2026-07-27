// polyglot-family: objects_and_dispatch
// polyglot-concept: inheritance_dynamic_dispatch_and_super
// polyglot-related: languages/go/language/
// polyglot-related+: 06_structs_methods_embedding_and_interfaces/test_045_implicit_interface_satisfaction_test.go
//
// 共同问题：复用实现与动态分派如何形成；调用父实现是否有专门机制。
// 对照观察：Go 没有 class inheritance 或 super；embedding 做组合，interface value 按动态类型分派。
package inheritance_dynamic_dispatch_and_super

import "testing"

type namedComponent struct{ name string }

func (value namedComponent) Label() string { return "base:" + value.name }

type serviceComponent struct {
	namedComponent
}

func (value serviceComponent) Label() string { return "service:" + value.name }

type labeler interface{ Label() string }

func TestEmbeddingAndInterfaceDispatchAreNotInheritance(t *testing.T) {
	service := serviceComponent{namedComponent: namedComponent{name: "api"}}
	var dynamic labeler = service
	if dynamic.Label() != "service:api" || service.namedComponent.Label() != "base:api" {
		t.Fatal("外层方法参与 interface 分派；调用嵌入实现需显式 selector，不存在 super")
	}
}
