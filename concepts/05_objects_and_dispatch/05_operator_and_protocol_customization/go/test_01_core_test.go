// polyglot-family: objects_and_dispatch
// polyglot-concept: operator_and_protocol_customization
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_098_stringer_and_formatter_test.go
//
// 共同问题：用户类型能否定制运算符、转换和语言协议；失败发生在编译期还是运行期。
// 对照观察：Go 不允许用户重载运算符；行为扩展通过小 interface（如 Stringer）和普通方法完成。
package operator_and_protocol_customization

import (
	"fmt"
	"testing"
)

type distance int

func (value distance) String() string { return fmt.Sprintf("%dm", value) }
func (value distance) Add(other distance) distance {
	return value + other
}

func TestExplicitMethodReplacesOperatorOverloading(t *testing.T) {
	value := distance(2).Add(distance(3))
	if value != 5 || fmt.Sprint(value) != "5m" {
		t.Fatal("Add 是显式领域操作；Stringer 只定制 fmt 协议，不改变 + 或转换语义")
	}
}
