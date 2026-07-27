// polyglot-covers: go.io.pipe-and-scanner
package ioworkflows_test

import (
	"bufio"
	"io"
	"slices"
	"testing"
)

func TestPipeProvidesStreamingBackpressureAndScannerTokenization(t *testing.T) {
	reader, writer := io.Pipe()
	writeResult := make(chan error, 1)
	go func() {
		payload := []byte("first\nsecond\n")
		count, writeErr := writer.Write(payload)
		closeErr := writer.CloseWithError(writeErr)
		if writeErr != nil {
			writeResult <- writeErr
		} else if count != len(payload) {
			writeResult <- io.ErrShortWrite
		} else {
			writeResult <- closeErr
		}
	}()
	scanner := bufio.NewScanner(reader)
	lines := []string{}
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(lines, []string{"first", "second"}) {
		t.Fatalf("Pipe 同步生产与消费；Scanner 按 split function 产出 token: %v", lines)
	}
	if err := <-writeResult; err != nil {
		t.Fatalf("PipeWriter 写入与关闭必须成功: %v", err)
	}
	if err := reader.Close(); err != nil {
		t.Fatalf("PipeReader 必须可靠关闭: %v", err)
	}
}
