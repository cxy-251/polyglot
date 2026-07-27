// polyglot-covers: go.runtime.version-architecture-capabilities
package runtimeintrospection_test

import (
	"runtime"
	"strings"
	"testing"
)

func TestRuntimeReportsLockedVersionAndBuildTarget(t *testing.T) {
	if runtime.Version() != "go1.26.5" {
		t.Fatalf("课程锁定 Go 1.26.5，实际 %s", runtime.Version())
	}
	if runtime.GOOS == "" || runtime.GOARCH == "" || runtime.NumCPU() < 1 {
		t.Fatal("GOOS/GOARCH 是构建目标；NumCPU 是当前运行时能力观察")
	}
	if !strings.HasPrefix(runtime.Version(), "go") {
		t.Fatal("release toolchain version 使用 go 前缀")
	}
}
