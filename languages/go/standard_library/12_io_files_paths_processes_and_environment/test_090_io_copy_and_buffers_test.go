// polyglot-covers: go.io.copy-and-buffers
package ioworkflows_test

import (
	"bytes"
	"io"
	"strings"
	"testing"
)

func TestCopyStreamsUntilEOF(t *testing.T) {
	var destination bytes.Buffer
	count, err := io.Copy(&destination, strings.NewReader("stream"))
	if err != nil || count != 6 || destination.String() != "stream" {
		t.Fatalf("io.Copy 连接 Reader 与 Writer，并报告已复制 byte 数: %d %q %v", count, &destination, err)
	}
	if _, err := destination.WriteString("-buffered"); err != nil {
		t.Fatal(err)
	}
}
