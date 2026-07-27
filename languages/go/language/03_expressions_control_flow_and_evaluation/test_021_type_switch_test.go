// polyglot-covers: go.statements.type-switch
package controlflow_test

import "testing"

func describeDynamicValue(value any) string {
	switch typed := value.(type) {
	case nil:
		return "nil"
	case int:
		return "int"
	case string:
		return "string:" + typed
	default:
		return "other"
	}
}

func TestTypeSwitchMatchesInterfaceDynamicType(t *testing.T) {
	if describeDynamicValue(nil) != "nil" ||
		describeDynamicValue(3) != "int" ||
		describeDynamicValue("go") != "string:go" {
		t.Fatal("type switch 按 interface 的动态类型选择分支")
	}
}
