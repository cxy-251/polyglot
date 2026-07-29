// polyglot-covers: go.http.request-response-handlers-and-middleware
package networkworkflows_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func withHeader(next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("X-Course", "go")
		next.ServeHTTP(writer, request)
	})
}

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

func TestMiddlewareWrapsHandlerContract(t *testing.T) {
	handler := withHeader(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusCreated)
	}))
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, httptest.NewRequest(http.MethodPost, "/items", nil))
	if recorder.Code != http.StatusCreated || recorder.Header().Get("X-Course") != "go" {
		t.Fatal("middleware 通过 Handler 组合横切行为，不需要继承框架基类")
	}
}
