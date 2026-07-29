// polyglot-covers: go.errors.values-sentinels-and-typed-details
package errorscleanup_test

import (
	"errors"
	"fmt"
	"testing"
)

var errUnavailable = errors.New("unavailable")

type validationError struct{ Field string }

func (err *validationError) Error() string { return "invalid " + err.Field }

func fetchValue(ready bool) (int, error) {
	if !ready {
		return 0, errUnavailable
	}
	return 7, nil
}

func TestErrorsAsFindsTypedErrorThroughWrapping(t *testing.T) {
	err := fmt.Errorf("save: %w", &validationError{Field: "name"})
	var target *validationError
	if !errors.As(err, &target) || target.Field != "name" {
		t.Fatal("errors.As 沿 Unwrap 链按可赋值类型提取详细信息")
	}
}

func TestExpectedFailureTravelsAsOrdinaryErrorValue(t *testing.T) {
	_, err := fetchValue(false)
	if !errors.Is(err, errUnavailable) {
		t.Fatal("调用方显式检查 error；sentinel 用 errors.Is 保留身份语义")
	}
}
