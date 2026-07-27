// polyglot-covers: go.binary.byte-slice-view-copy
package serialization_test

import "testing"

func TestSubsliceAliasesUntilExplicitCopy(t *testing.T) {
	source := []byte{1, 2, 3}
	view := source[1:]
	clone := append([]byte(nil), view...)
	view[0] = 9
	if source[1] != 9 || clone[0] != 2 {
		t.Fatal("subslice 是共享 view；显式 copy/append 到新 slice 才隔离所有权")
	}
}
