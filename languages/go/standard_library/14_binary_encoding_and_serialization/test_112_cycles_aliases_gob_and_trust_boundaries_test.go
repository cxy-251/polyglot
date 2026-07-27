// polyglot-covers: go.serialization.cycles-aliases-gob-trust
package serialization_test

import (
	"bytes"
	"encoding/gob"
	"encoding/json"
	"testing"
)

type cycleNode struct {
	Value int
	Next  *cycleNode
}

func TestSerializationHasGraphAndTrustBoundaries(t *testing.T) {
	node := &cycleNode{Value: 1}
	node.Next = node
	if _, err := json.Marshal(node); err == nil {
		t.Fatal("JSON 是树形数据模型，cycle 会返回错误")
	}

	var buffer bytes.Buffer
	source := map[string]int{"value": 7}
	if err := gob.NewEncoder(&buffer).Encode(source); err != nil {
		t.Fatal(err)
	}
	var decoded map[string]int
	if err := gob.NewDecoder(&buffer).Decode(&decoded); err != nil || decoded["value"] != 7 {
		t.Fatalf("gob 为 Go 值传输类型和值信息: %v %v", decoded, err)
	}
	// 解码不可信数据前仍需限制大小和结构；编码格式不会自动提供认证或资源配额。
}
