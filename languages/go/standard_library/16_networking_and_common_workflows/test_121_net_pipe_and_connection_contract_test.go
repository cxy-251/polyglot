// polyglot-covers: go.net.pipe-connection-contract
package networkworkflows_test

import (
	"io"
	"net"
	"testing"
)

func TestNetPipeProvidesInMemoryConnectionWithoutRealNetwork(t *testing.T) {
	client, server := net.Pipe()
	t.Cleanup(func() {
		if err := client.Close(); err != nil {
			t.Errorf("client close: %v", err)
		}
	})
	serverResult := make(chan error, 1)
	go func() {
		payload := []byte("reply")
		count, writeErr := server.Write(payload)
		closeErr := server.Close()
		if writeErr != nil {
			serverResult <- writeErr
		} else if count != len(payload) {
			serverResult <- io.ErrShortWrite
		} else {
			serverResult <- closeErr
		}
	}()
	payload, err := io.ReadAll(client)
	if err != nil || string(payload) != "reply" {
		t.Fatalf("net.Pipe 可在不监听真实网络端口时传输字节: %q %v", payload, err)
	}
	if err := <-serverResult; err != nil {
		t.Fatalf("server write/close: %v", err)
	}
}
