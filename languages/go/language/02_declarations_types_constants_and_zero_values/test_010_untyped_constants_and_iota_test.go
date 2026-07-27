// polyglot-covers: go.constants.untyped-iota
package declarations_test

import "testing"

const (
	readPermission = 1 << iota
	writePermission
	executePermission
)

func TestUntypedConstantsDelayConcreteRepresentation(t *testing.T) {
	const exact = 1 << 40
	var wide int64 = exact
	if wide != 1099511627776 {
		t.Fatal("未类型化常量在赋值上下文才检查目标表示范围")
	}
	if readPermission|writePermission|executePermission != 7 {
		t.Fatal("iota 在 const 组中按 ConstSpec 递增")
	}
}
