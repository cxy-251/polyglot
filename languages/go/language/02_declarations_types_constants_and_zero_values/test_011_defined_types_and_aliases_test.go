// polyglot-covers: go.types.defined-and-alias
package declarations_test

import "testing"

type UserID int
type UserIDAlias = UserID

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
