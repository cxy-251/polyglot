package initfixture

var Events = []string{"variable"}

func init() {
	Events = append(Events, "init")
}
