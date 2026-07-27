// polyglot-covers: go.statements.if-and-expression-switch
package controlflow_test

import "testing"

func TestIfAndSwitchMayOwnShortDeclarations(t *testing.T) {
	classification := ""
	if value := 7; value%2 == 1 {
		classification = "odd"
	}
	switch length := len(classification); {
	case length == 0:
		t.Fatal("应有分类")
	case length < 4:
		classification += "-short"
	default:
		classification += "-long"
	}
	if classification != "odd-short" {
		t.Fatalf("switch 默认不 fallthrough: %q", classification)
	}
}
