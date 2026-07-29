// polyglot-covers: go.packages.namespace-exports-internal-and-import-identity
package packagesmodules_test

import (
	jsoncodec "encoding/json"
	"testing"

	"polyglot.local/go-course/internal/secret"
)

func TestPackageQualifiedNamesAndCapitalizationControlAccess(t *testing.T) {
	encoded, err := jsoncodec.Marshal(map[string]int{"value": 3})
	if err != nil || string(encoded) != `{"value":3}` {
		t.Fatalf("import alias 只改变当前文件绑定，不改变 package 身份: %s %v", encoded, err)
	}
	if secret.Exported == "" || secret.HiddenLength() == 0 {
		t.Fatal("首字母大写标识符可跨 package 访问，未导出状态只能通过导出 API 观察")
	}
	// internal package 只允许其父目录树内的 importer；v2+ module 通常以 `/vN` 进入 import identity。
}
