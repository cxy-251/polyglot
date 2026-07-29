// polyglot-harness: go.gofmt_parser_and_vet
package goharness_test

import (
	"go/format"
	"os/exec"
	"strings"
	"testing"
)

func TestFormattingAndStaticAnalysisHaveDifferentJobs(t *testing.T) {
	formatted, err := format.Source([]byte("package p\nfunc f(){println(\"ok\")}\n"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(formatted), "func f() {") {
		t.Fatalf("gofmt 负责确定规范布局: %s", formatted)
	}
	output, err := exec.Command("go", "help", "vet").CombinedOutput()
	if err != nil || !strings.Contains(string(output), "reports diagnostics") {
		t.Fatalf("go vet 是静态诊断入口，不是格式化器: %s", output)
	}
}
