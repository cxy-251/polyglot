// polyglot-harness: go.list_and_env
package goharness_test

import (
	"os/exec"
	"strings"
	"testing"
)

func TestGoListAndEnvExposeBuildContext(t *testing.T) {
	listed, err := exec.Command("go", "list", "-f", "{{.ImportPath}}", ".").CombinedOutput()
	if err != nil {
		t.Fatal(err)
	}
	if got := strings.TrimSpace(string(listed)); got == "" {
		t.Fatal("go list 应解析当前 package 的 import path")
	}
	env, err := exec.Command("go", "env", "GOOS", "GOARCH", "GOROOT").CombinedOutput()
	if err != nil {
		t.Fatal(err)
	}
	if len(strings.Fields(string(env))) != 3 {
		t.Fatalf("go env 应分别输出三个值: %q", env)
	}
}
