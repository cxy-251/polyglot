// polyglot-covers: go.modules.internal-and-semantic-import-version
package packagesmodules_test

import (
	"runtime/debug"
	"strings"
	"testing"

	"polyglot.local/go-course/internal/secret"
)

func TestInternalPackageIsVisibleOnlyBelowItsParent(t *testing.T) {
	if secret.Exported == "" {
		t.Fatal("当前 import 路径位于 polyglot.local/go-course 父树内，因此可导入 internal")
	}
	info, ok := debug.ReadBuildInfo()
	if !ok || !strings.HasPrefix(info.Main.Path, "polyglot.local/go-course") {
		t.Fatalf("build info 应保留 main module path: %+v", info)
	}
	// v2+ module 的路径通常必须带 `/vN`；这是 import identity，不只是下载标签。
}
