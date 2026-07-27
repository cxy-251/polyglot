// polyglot-covers: go.os.environment-and-working-directory
package ioworkflows_test

import (
	"os"
	"testing"
)

func TestEnvironmentAndWorkingDirectoryAreProcessGlobal(t *testing.T) {
	t.Setenv("POLYGLOT_GO_ENV", "isolated")
	if os.Getenv("POLYGLOT_GO_ENV") != "isolated" {
		t.Fatal("t.Setenv 在测试结束时恢复环境变量")
	}
	original, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		if restoreErr := os.Chdir(original); restoreErr != nil {
			t.Errorf("恢复工作目录: %v", restoreErr)
		}
	}()
	if err := os.Chdir(t.TempDir()); err != nil {
		t.Fatal(err)
	}
	// Chdir 影响整个进程，因此此类测试不能与依赖 cwd 的测试并行。
}
