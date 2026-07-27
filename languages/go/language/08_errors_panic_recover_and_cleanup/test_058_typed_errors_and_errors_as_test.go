// polyglot-covers: go.errors.typed-errors-as
package errorscleanup_test

import (
	"errors"
	"fmt"
	"testing"
)

type validationError struct{ Field string }

func (err *validationError) Error() string { return "invalid " + err.Field }

func TestErrorsAsFindsTypedErrorThroughWrapping(t *testing.T) {
	err := fmt.Errorf("save: %w", &validationError{Field: "name"})
	var target *validationError
	if !errors.As(err, &target) || target.Field != "name" {
		t.Fatal("errors.As 沿 Unwrap 链按可赋值类型提取详细信息")
	}
}
