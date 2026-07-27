// polyglot-covers: go.io.reader-writer-partial-operations
package ioworkflows_test

import (
	"io"
	"strings"
	"testing"
)

type oneByteReader struct{ source *strings.Reader }

func (reader oneByteReader) Read(target []byte) (int, error) {
	if len(target) > 1 {
		target = target[:1]
	}
	return reader.source.Read(target)
}

func TestReaderConsumersMustHandleShortReads(t *testing.T) {
	buffer := make([]byte, 3)
	count, err := io.ReadFull(oneByteReader{strings.NewReader("abc")}, buffer)
	if err != nil || count != 3 || string(buffer) != "abc" {
		t.Fatalf("Reader 可合法返回短读；ReadFull 负责循环补满: %d %q %v", count, buffer, err)
	}
}
