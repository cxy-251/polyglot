// polyglot-covers: go.net-url.parsing-and-resolution
package networkworkflows_test

import (
	"net/url"
	"testing"
)

func TestURLSeparatesEncodedAndDecodedComponents(t *testing.T) {
	base, err := url.Parse("https://example.test/a/b/")
	if err != nil {
		t.Fatal(err)
	}
	reference, err := url.Parse("../item?q=go+course#part")
	if err != nil {
		t.Fatal(err)
	}
	resolved := base.ResolveReference(reference)
	if resolved.String() != "https://example.test/a/item?q=go+course#part" ||
		resolved.Query().Get("q") != "go course" {
		t.Fatalf("URL resolution 理解 scheme、path、query 与 fragment: %s", resolved)
	}
}
