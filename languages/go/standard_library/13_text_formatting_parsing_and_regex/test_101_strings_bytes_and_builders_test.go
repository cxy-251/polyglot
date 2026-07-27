// polyglot-covers: go.text.strings-bytes-builders
package textprocessing_test

import (
	"bytes"
	"strings"
	"testing"
)

func TestStringAndByteHelpersUseDifferentMutationModels(t *testing.T) {
	if strings.TrimSpace(" go \n") != "go" {
		t.Fatal("strings 操作不可变 UTF-8 文本值并返回新 string")
	}
	buffer := bytes.NewBufferString("go")
	buffer.WriteByte('!')
	if buffer.String() != "go!" {
		t.Fatal("bytes.Buffer 维护可增长 byte 序列")
	}
	var builder strings.Builder
	builder.WriteString("course")
	if builder.String() != "course" {
		t.Fatal("strings.Builder 为只追加 string 构建优化，非零值复制后不可继续使用")
	}
}
