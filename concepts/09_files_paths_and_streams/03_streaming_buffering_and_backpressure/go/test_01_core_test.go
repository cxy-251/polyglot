// polyglot-family: files_paths_and_streams
// polyglot-concept: streaming_buffering_and_backpressure
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_091_pipe_and_scanner_test.go
//
// 共同问题：流如何表达短读写、缓冲和背压；完成与错误从哪里传播。
// 对照观察：Reader/Writer 允许部分进度；io.Pipe 的同步写入在 reader 消费前形成背压。
package streaming_buffering_and_backpressure

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"testing"
)

func TestPipeAndBufferedWriterExposeExplicitFlushBoundaries(t *testing.T) {
	reader, writer := io.Pipe()
	writeResult := make(chan error, 1)
	go func() {
		count, err := writer.Write([]byte("payload"))
		if err == nil && count != len("payload") {
			err = fmt.Errorf("io.PipeWriter short write: %d", count)
		}
		writeResult <- err
	}()

	first := make([]byte, 1)
	if count, err := reader.Read(first); err != nil || count != 1 || string(first) != "p" {
		t.Fatalf("reader 先取得 writer 提供的首个 byte: %d %q %v", count, first, err)
	}
	select {
	case err := <-writeResult:
		t.Fatalf("io.PipeWriter 不应在剩余 byte 被读取前完成: %v", err)
	default:
	}
	remaining := make([]byte, len("payload")-1)
	if _, err := io.ReadFull(reader, remaining); err != nil || string(remaining) != "ayload" {
		t.Fatalf("reader 消费剩余 byte 后 writer 才能完成: %q %v", remaining, err)
	}
	if err := <-writeResult; err != nil {
		t.Fatal(err)
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := reader.Close(); err != nil {
		t.Fatal(err)
	}

	var destination bytes.Buffer
	buffered := bufio.NewWriter(&destination)
	if count, err := buffered.WriteString("queued"); err != nil || count != len("queued") {
		t.Fatalf("buffered writer 接收完整输入并报告进度: %d %v", count, err)
	}
	if destination.Len() != 0 {
		t.Fatal("缓冲写入在 Flush 前不一定到达下游")
	}
	if err := buffered.Flush(); err != nil || destination.String() != "queued" {
		t.Fatalf("Flush 是显式提交和错误边界: %q %v", &destination, err)
	}
}
