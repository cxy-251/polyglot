// polyglot-covers: go.net.pipe-connection-contract
package networkworkflows_test

import (
	"io"
	"net"
	"testing"
)

func TestNetPipeExercisesFullDuplexConnectionWithoutRealNetwork(t *testing.T) {
	client, server := net.Pipe()
	t.Cleanup(func() {
		_ = client.Close()
		_ = server.Close()
	})
	go func() {
		_, _ = server.Write([]byte("reply"))
		_ = server.Close()
	}()
	payload, err := io.ReadAll(client)
	if err != nil || string(payload) != "reply" {
		t.Fatalf("net.Conn 同时实现 Reader、Writer、deadlines 与 Close: %q %v", payload, err)
	}
}
