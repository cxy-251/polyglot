// polyglot-covers: go.types.constants-defined-types-and-aliases
package declarations_test

import "testing"

const (
	readPermission = 1 << iota
	writePermission
	executePermission
)

type UserID int
type UserIDAlias = UserID

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

func TestDefinedTypeCreatesIdentityWhileAliasDoesNot(t *testing.T) {
	var id UserID = 7
	var alias UserIDAlias = id
	if alias != id {
		t.Fatal("alias 与目标类型完全相同")
	}
	var raw int = int(id)
	if raw != 7 {
		t.Fatal("defined type 与底层 int 不同，跨类型赋值需要显式转换")
	}
}
