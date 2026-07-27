// polyglot-family: values_and_comparison
// polyglot-concept: truthiness
// polyglot-related: languages/go/language/
// polyglot-related+: 03_expressions_control_flow_and_evaluation/test_017_operators_and_boolean_conditions_test.go
//
// 共同问题：条件接受哪些值；零值、空集合和自定义值能否隐式决定真假。
// 对照观察：Go 条件必须是 bool，没有 Python truth protocol 或 JavaScript ToBoolean。
package truthiness

import (
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"testing"
)

func TestConditionsRequireBooleanExpressions(t *testing.T) {
	zero := 0
	empty := []int{}
	if !(zero == 0) || !(len(empty) == 0) {
		t.Fatal("零值和空集合必须显式形成 bool 表达式")
	}
	source := `package p; func f() { if 0 {} }`
	fileSet := token.NewFileSet()
	file, err := parser.ParseFile(fileSet, "invalid.go", source, 0)
	if err != nil {
		t.Fatal(err)
	}
	_, err = (&types.Config{}).Check("p", fileSet, []*ast.File{file}, nil)
	if err == nil {
		t.Fatal("Go 不把数字隐式转换为 bool")
	}
}
