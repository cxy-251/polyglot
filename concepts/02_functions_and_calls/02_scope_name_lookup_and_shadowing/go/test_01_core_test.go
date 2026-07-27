// polyglot-family: functions_and_calls
// polyglot-concept: scope_name_lookup_and_shadowing
// polyglot-related: languages/go/language/
// polyglot-related+: 02_declarations_types_constants_and_zero_values/test_009_var_const_and_short_declarations_test.go
//
// 共同问题：名称从哪里解析；内层声明如何遮蔽外层绑定；离开作用域后哪个值仍存在。
// 对照观察：Go 使用词法块作用域；短声明可能在同一行复用旧变量并引入新变量。
package scope_name_lookup_and_shadowing

import "testing"

func TestInnerDeclarationShadowsWithoutChangingOuterBinding(t *testing.T) {
	value := "outer"
	observed := ""
	{
		value := "inner"
		observed = value
	}
	if observed != "inner" || value != "outer" {
		t.Fatal("内层 := 创建新绑定，块结束后外层绑定重新可见")
	}
	number, err := 1, error(nil)
	number, text := 2, "new"
	if number != 2 || text != "new" || err != nil {
		t.Fatal("同一作用域短声明至少引入一个新名时，可同时赋值已有变量")
	}
}
