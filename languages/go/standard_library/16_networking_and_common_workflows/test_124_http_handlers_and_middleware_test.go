// polyglot-covers: go.http.handlers-and-middleware
package networkworkflows_test

import (
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
