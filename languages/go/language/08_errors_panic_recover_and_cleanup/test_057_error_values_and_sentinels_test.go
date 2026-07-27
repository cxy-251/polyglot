// polyglot-covers: go.errors.values-and-sentinels
package errorscleanup_test

import (
	"errors"
	"testing"
)

var errUnavailable = errors.New("unavailable")

func fetchValue(ready bool) (int, error) {
	if !ready {
		return 0, errUnavailable
	}
	return 7, nil
}

func TestExpectedFailureTravelsAsOrdinaryErrorValue(t *testing.T) {
	_, err := fetchValue(false)
	if !errors.Is(err, errUnavailable) {
		t.Fatal("调用方显式检查 error；sentinel 用 errors.Is 保留身份语义")
	}
}
