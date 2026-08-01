# frozen_string_literal: true
# polyglot-covers: ruby.text.regexp-captures-and-lookaround

require "assertions"

A = PolyglotAssertions

A.case("anchoring, named captures and lookaround shape a MatchData result") do
  pattern = /\A(?<name>[a-z]+)-(?<number>\d+)(?=!)!\z/
  match = pattern.match("ruby-40!")
  A.equal("ruby", match[:name])
  A.equal("40", match[:number])
  A.equal(["ruby", "40"], match.captures)
  A.equal({"name" => "ruby", "number" => "40"}, match.named_captures)
  A.nil_value(pattern.match("ruby-40"))
  A.truth(/(?<!not )ready/.match?("ready"))
  A.falsey(/(?<!not )ready/.match?("not ready"))
end

A.case("gsub exposes per-match state while replacement strings interpret backreferences") do
  text = "a1 b2"
  observed = []
  replaced = text.gsub(/(?<letter>[a-z])(?<number>\d)/) do
    current = Regexp.last_match
    observed << [current[:letter], current[:number]]
    "#{current[:letter].upcase}#{current[:number]}"
  end
  A.equal("A1 B2", replaced)
  A.equal([["a", "1"], ["b", "2"]], observed)
  A.equal("a[1] b[2]", text.gsub(/(\d)/, '[\1]'))
  A.equal(["1", "2"], text.scan(/\d/))
end

A.done
