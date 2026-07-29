// polyglot-covers: go.http.request-context-cancellation
package networkworkflows_test

import (
	"context"
	"errors"
	"net/http"
	"testing"
)

type cancellationTransport struct {
	started chan<- struct{}
}

func (transport cancellationTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	close(transport.started)
	<-request.Context().Done()
	return nil, request.Context().Err()
}

func TestRequestContextCancelsAnInFlightExchange(t *testing.T) {
	started := make(chan struct{})
	client := &http.Client{
		Transport: cancellationTransport{started: started},
	}
	contextValue, cancel := context.WithCancel(context.Background())
	request, err := http.NewRequestWithContext(contextValue, http.MethodGet, "https://example.test", nil)
	if err != nil {
		t.Fatal(err)
	}
	result := make(chan error, 1)
	go func() {
		_, requestErr := client.Do(request)
		result <- requestErr
	}()
	<-started
	cancel()
	err = <-result
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("request context 取消必须传递到 in-flight RoundTripper: %v", err)
	}
}
