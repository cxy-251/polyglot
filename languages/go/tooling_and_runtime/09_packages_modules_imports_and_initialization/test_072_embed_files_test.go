// polyglot-covers: go.embed.files
package packagesmodules_test

import (
	_ "embed"
	"strings"
	"testing"
)

//go:embed fixture.txt
var embeddedFixture string

func TestEmbedCapturesFileAtBuildTime(t *testing.T) {
	if strings.TrimSpace(embeddedFixture) != "embedded course fixture" {
		t.Fatalf("embed 变量由构建器填充，不在运行时读取工作目录: %q", embeddedFixture)
	}
}
