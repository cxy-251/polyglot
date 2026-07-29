// polyglot-covers: go.structs.values-embedding-and-layout-boundary
package objects_test

import (
	"testing"
	"unsafe"
)

type layoutRecord struct {
	flag  byte
	count int64
}

type embeddedName struct{ Name string }
type embeddedRecord struct {
	embeddedName
	ID int
}

func TestStructAssignmentCopiesFieldsAndLayoutMayContainPadding(t *testing.T) {
	original := layoutRecord{flag: 1, count: 2}
	copied := original
	copied.count = 9
	if original.count != 2 || copied == original {
		t.Fatal("struct 是值；修改副本字段不回写原值")
	}
	if unsafe.Sizeof(original) < unsafe.Sizeof(original.flag)+unsafe.Sizeof(original.count) {
		t.Fatal("对象尺寸不会小于字段尺寸之和")
	}
	// 字段偏移与 padding 属于实现布局，不应用手写常量跨架构推断。
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
