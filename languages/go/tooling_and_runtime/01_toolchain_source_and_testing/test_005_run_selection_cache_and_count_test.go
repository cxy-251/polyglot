// polyglot-covers: go.testing.run-selection-cache-count
package toolchaintesting_test

import (
	"os/exec"
	"strings"
	"testing"
)

func TestGoHelpListsRunSelectionAndCountFlags(t *testing.T) {
	output, err := exec.Command("go", "help", "testflag").CombinedOutput()
	if err != nil {
		t.Fatal(err)
	}
	help := string(output)
	for _, flag := range []string{"-run regexp", "-count n"} {
		if !strings.Contains(help, flag) {
			t.Fatalf("锁定工具链帮助缺少 %q", flag)
		}
	}
	// `-run` 只选择匹配名称；`-count=1` 使成功结果不从 test cache 复用。
}
