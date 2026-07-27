// polyglot-covers: go.structs.values-and-layout-boundary
package objects_test

import (
	"testing"
	"unsafe"
)

type layoutRecord struct {
	flag  byte
	count int64
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
