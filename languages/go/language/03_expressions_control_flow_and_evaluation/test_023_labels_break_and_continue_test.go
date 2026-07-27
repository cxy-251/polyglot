// polyglot-covers: go.statements.labels-break-continue
package controlflow_test

import "testing"

func TestLabelsTargetAnEnclosingLoop(t *testing.T) {
	visited := []int{}
outer:
	for row := 0; row < 3; row++ {
		for column := 0; column < 3; column++ {
			if column == 1 {
				continue outer
			}
			visited = append(visited, row*10+column)
		}
	}
	if len(visited) != 3 || visited[2] != 20 {
		t.Fatalf("带标签 continue 跳到指定外层循环: %v", visited)
	}
}
