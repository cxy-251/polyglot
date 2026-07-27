// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 14_binary_encoding_and_serialization/test_108_json_tags_omitted_missing_and_null_test.go
//
// 共同问题：序列化保留哪些类型、别名和缺失状态；对象图中的 cycle 如何处理。
// 对照观察：encoding/json 面向树形数据；struct tag 控制字段，pointer 区分值与 null，但不保留别名。
package serialization_clone_and_transfer

import (
	"encoding/json"
	"testing"
)

type transferNode struct {
	Value int           `json:"value"`
	Next  *transferNode `json:"next,omitempty"`
}

func TestJSONRoundTripCreatesIndependentTreeAndRejectsCycles(t *testing.T) {
	source := &transferNode{Value: 1, Next: &transferNode{Value: 2}}
	encoded, err := json.Marshal(source)
	if err != nil {
		t.Fatal(err)
	}
	var decoded transferNode
	if err := json.Unmarshal(encoded, &decoded); err != nil {
		t.Fatal(err)
	}
	decoded.Next.Value = 9
	if source.Next.Value != 2 {
		t.Fatal("序列化 round trip 创建新值，不保留 pointer alias")
	}
	source.Next = source
	if _, err := json.Marshal(source); err == nil {
		t.Fatal("cycle 不能表示为 JSON tree")
	}
}
