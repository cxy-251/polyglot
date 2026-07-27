// polyglot-covers: go.interfaces.assertions-and-type-switch
package objects_test

import "testing"

func TestCommaOkAssertionAvoidsPanic(t *testing.T) {
	var value any = "go"
	text, ok := value.(string)
	_, integerOK := value.(int)
	if text != "go" || !ok || integerOK {
		t.Fatal("comma-ok assertion 报告动态类型是否匹配")
	}
	switch value.(type) {
	case string:
		return
	default:
		t.Fatal("type switch 应匹配 string 动态类型")
	}
}
