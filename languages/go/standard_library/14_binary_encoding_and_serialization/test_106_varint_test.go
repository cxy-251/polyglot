// polyglot-covers: go.encoding-binary.varint
package serialization_test

import (
	"encoding/binary"
	"testing"
)

func TestVarintUsesVariableLengthAndReportsMalformedInput(t *testing.T) {
	buffer := make([]byte, binary.MaxVarintLen64)
	written := binary.PutVarint(buffer, -300)
	value, read := binary.Varint(buffer[:written])
	if value != -300 || read != written {
		t.Fatalf("PutVarint/Varint 使用有符号编码往返: %d %d %d", value, read, written)
	}
	_, read = binary.Uvarint([]byte{0x80})
	if read != 0 {
		t.Fatal("read=0 表示缓冲区不足；负数表示编码溢出")
	}
}
