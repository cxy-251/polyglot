// polyglot-covers: go.encoding-binary.byte-order-and-varints
package serialization_test

import (
	"encoding/binary"
	"slices"
	"testing"
)

func TestByteOrderMustBeChosenExplicitly(t *testing.T) {
	buffer := make([]byte, 4)
	binary.BigEndian.PutUint32(buffer, 0x01020304)
	if !slices.Equal(buffer, []byte{1, 2, 3, 4}) {
		t.Fatalf("BigEndian 固定跨平台 wire order: %v", buffer)
	}
	if binary.LittleEndian.Uint32(buffer) != 0x04030201 {
		t.Fatal("相同 bytes 用不同 byte order 解码得到不同数值")
	}
}

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
