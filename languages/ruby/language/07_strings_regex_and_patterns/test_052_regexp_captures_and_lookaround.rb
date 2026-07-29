# frozen_string_literal: true
# polyglot-covers: ruby.text.regexp-captures-and-lookaround

require "assertions"

A = PolyglotAssertions

pattern = /\A(?<name>[a-z]+)-(?<number>\d+)(?=!)!\z/
match = pattern.match("ruby-40!")
A.equal("ruby", match[:name])
A.equal("40", match[:number])
A.equal(["ruby", "40"], match.captures)
A.equal({"name" => "ruby", "number" => "40"}, match.named_captures)
A.equal(0, match.begin(0))
A.equal(8, match.end(0))
A.nil_value(pattern.match("ruby-40"))
A.truth(/(?<!not )ready/.match?("ready"))
A.falsey(/(?<!not )ready/.match?("not ready"))

A.done
