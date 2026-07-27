// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 14_binary_encoding_and_serialization/test_105_binary_endianness_test.go
//
// 共同问题：buffer view 是否共享内存；多字节整数采用何种 byte order；复制何时发生。
// 对照观察：Go []byte subslice 共享 backing array；encoding/binary 要求显式选择端序。
package binary_buffers_views_and_endianness

import (
	"encoding/binary"
	"testing"
)

func TestSubsliceAliasesAndByteOrderIsExplicit(t *testing.T) {
	buffer := []byte{0, 0, 0, 0}
	view := buffer[1:3]
	binary.BigEndian.PutUint16(view, 0x0102)
	if buffer[1] != 1 || buffer[2] != 2 {
		t.Fatal("subslice 写入同一 backing array")
	}
	clone := append([]byte(nil), view...)
	view[0] = 9
	if clone[0] != 1 {
		t.Fatal("显式复制后 buffer 所有权分离")
	}
}
