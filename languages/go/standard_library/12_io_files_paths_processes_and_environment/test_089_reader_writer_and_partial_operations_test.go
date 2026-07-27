// polyglot-covers: go.io.reader-writer-partial-operations
package ioworkflows_test

import (
	"bytes"
	"errors"
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

type oneByteWriter struct {
	destination bytes.Buffer
}

func (writer *oneByteWriter) Write(source []byte) (int, error) {
	if len(source) == 0 {
		return 0, nil
	}
	return writer.destination.Write(source[:1])
}

type invalidCountWriter struct{}

func (invalidCountWriter) Write(source []byte) (int, error) {
	return len(source) + 1, nil
}

func TestReaderConsumersMustHandleShortReads(t *testing.T) {
	buffer := make([]byte, 3)
	count, err := io.ReadFull(oneByteReader{strings.NewReader("abc")}, buffer)
	if err != nil || count != 3 || string(buffer) != "abc" {
		t.Fatalf("Reader 可合法返回短读；ReadFull 负责循环补满: %d %q %v", count, buffer, err)
	}
}

func TestWriterCallersMustInspectCountAndError(t *testing.T) {
	writer := &oneByteWriter{}
	count, err := writer.Write([]byte("abc"))
	if err != nil || count != 1 || writer.destination.String() != "a" {
		t.Fatalf("直接调用 Writer 必须同时检查 n 和 err: %d %q %v", count, &writer.destination, err)
	}

	count, err = io.WriteString(writer, "xyz")
	if err != nil || count != 1 || writer.destination.String() != "ax" {
		t.Fatalf("io.WriteString 对普通 Writer 只调用一次 Write，仍暴露短写结果: %d %q %v",
			count, &writer.destination, err)
	}
}

func TestCopyRejectsBrokenWriterContracts(t *testing.T) {
	shortWriter := &oneByteWriter{}
	count, err := io.Copy(shortWriter, io.LimitReader(strings.NewReader("abc"), 3))
	if count != 1 || !errors.Is(err, io.ErrShortWrite) {
		t.Fatalf("上层复制工具把 n < len(p) 且 err == nil 转成 ErrShortWrite: %d %v", count, err)
	}

	count, err = io.Copy(invalidCountWriter{}, io.LimitReader(strings.NewReader("abc"), 3))
	if err == nil {
		t.Fatalf("Writer 不得报告超过输入长度的 n；io.Copy 拒绝无效结果: %d", count)
	}
}
