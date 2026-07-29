// polyglot-harness: go.packages_and_files
package goharness

import "testing"

func TestFilesInOneDirectoryFormOnePackage(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatal("同一 package 的测试可直接调用被测声明")
	}
	// internal test package 与普通源码同包，因此也能观察未导出标识符。
	if internalLabel != "package-private" {
		t.Fatal("同包文件共享 package 级命名空间")
	}
}
