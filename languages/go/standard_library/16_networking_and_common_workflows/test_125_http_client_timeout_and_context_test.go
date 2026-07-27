// polyglot-covers: go.http.client-timeout-and-context
package networkworkflows_test

import (
	"context"
	"errors"
	"net/http"
	"testing"
	"time"
)

type waitForCancellationTransport struct{}

func (waitForCancellationTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	<-request.Context().Done()
	return nil, request.Context().Err()
}

func TestClientTimeoutCancelsRequestContext(t *testing.T) {
	client := &http.Client{
		Transport: waitForCancellationTransport{},
		Timeout:   20 * time.Millisecond,
	}
	request, err := http.NewRequestWithContext(context.Background(), http.MethodGet, "https://example.test", nil)
	if err != nil {
		t.Fatal(err)
	}
	_, err = client.Do(request)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("Client.Timeout 以 request context deadline 覆盖整个 exchange: %v", err)
	}
}
