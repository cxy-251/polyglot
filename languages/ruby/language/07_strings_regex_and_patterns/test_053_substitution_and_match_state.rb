# frozen_string_literal: true
# polyglot-covers: ruby.text.substitution-and-match-state

require "assertions"

A = PolyglotAssertions

text = "a1 b2"
A.equal("a[1] b[2]", text.gsub(/(\d)/, '[\1]'))

observed = []
replaced = text.gsub(/(?<letter>[a-z])(?<number>\d)/) do
  match = Regexp.last_match
  observed << [match[:letter], match[:number]]
  "#{match[:letter].upcase}#{match[:number]}"
end

A.equal("A1 B2", replaced)
A.equal([["a", "1"], ["b", "2"]], observed)
A.equal("aX bX", text.sub(/\d/, "X").sub(/\d/, "X"))
A.equal(["1", "2"], text.scan(/\d/))

A.done
