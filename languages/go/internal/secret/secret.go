package secret

const Exported = "visible inside parent module"

const hidden = "package private"

func HiddenLength() int {
	return len(hidden)
}
