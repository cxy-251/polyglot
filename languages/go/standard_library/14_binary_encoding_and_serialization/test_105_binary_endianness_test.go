// polyglot-covers: go.encoding-binary.endianness
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
