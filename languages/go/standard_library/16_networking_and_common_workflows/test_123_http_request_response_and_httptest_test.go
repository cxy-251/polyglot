// polyglot-covers: go.http.request-response-httptest
package networkworkflows_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHTTPTestServerUsesLoopbackAndRealProtocolStack(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("X-Method", request.Method)
		payload := []byte(request.URL.Query().Get("name"))
		if count, err := writer.Write(payload); err != nil || count != len(payload) {
			t.Errorf("response write: %d %v", count, err)
		}
	}))
	defer server.Close()
	response, err := server.Client().Get(server.URL + "?name=go")
	if err != nil {
		t.Fatal(err)
	}
	body, readErr := io.ReadAll(response.Body)
	closeErr := response.Body.Close()
	if readErr != nil || closeErr != nil || string(body) != "go" ||
		response.Header.Get("X-Method") != "GET" {
		t.Fatalf("httptest 在动态 loopback 端口验证 request/response: %q read=%v close=%v",
			body, readErr, closeErr)
	}
}
