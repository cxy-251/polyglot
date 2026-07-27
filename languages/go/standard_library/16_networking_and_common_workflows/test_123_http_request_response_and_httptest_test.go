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
		_, _ = writer.Write([]byte(request.URL.Query().Get("name")))
	}))
	defer server.Close()
	response, err := server.Client().Get(server.URL + "?name=go")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	if err != nil || string(body) != "go" || response.Header.Get("X-Method") != "GET" {
		t.Fatalf("httptest 在动态 loopback 端口验证 request/response: %q %v", body, err)
	}
}
