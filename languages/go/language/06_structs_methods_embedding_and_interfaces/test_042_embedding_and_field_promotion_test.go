// polyglot-covers: go.structs.embedding-and-promotion
package objects_test

import "testing"

type embeddedName struct{ Name string }
type embeddedRecord struct {
	embeddedName
	ID int
}

func TestEmbeddingPromotesSelectorsWithoutCreatingInheritance(t *testing.T) {
	record := embeddedRecord{embeddedName: embeddedName{Name: "Go"}, ID: 1}
	if record.Name != "Go" || record.embeddedName.Name != "Go" {
		t.Fatal("嵌入字段可通过提升后的 selector 访问")
	}
	record.Name = "Gopher"
	if record.embeddedName.Name != "Gopher" {
		t.Fatal("提升 selector 指向真实嵌入字段，不是复制属性")
	}
	// embedding 提供组合和名称提升，不建立 class/subclass 关系。
}
