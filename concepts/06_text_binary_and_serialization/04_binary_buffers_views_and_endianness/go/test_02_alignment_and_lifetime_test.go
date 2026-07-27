// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_119_struct_tags_size_and_alignment_test.go
//
// 共同问题：二进制 view 是否要求 alignment；底层存储生命周期怎样影响 view。
// 对照观察：encoding/binary 从 []byte 解码，不要求 CPU 对齐；slice 引用会保持 backing array 存活。
package binary_buffers_views_and_endianness

import (
	"encoding/binary"
	"testing"
)

func unalignedView() []byte {
	buffer := []byte{0xff, 1, 2, 3, 4}
	return buffer[1:]
}

func TestByteDecoderDoesNotRequireAlignedPointerCast(t *testing.T) {
	view := unalignedView()
	if binary.BigEndian.Uint32(view) != 0x01020304 {
		t.Fatal("byte 解码按索引读取；返回 slice 使 backing array 在需要期间保持存活")
	}
	// 将任意 []byte 用 unsafe 强转为更严格对齐类型会引入平台约束，不是 encoding/binary 的要求。
}
