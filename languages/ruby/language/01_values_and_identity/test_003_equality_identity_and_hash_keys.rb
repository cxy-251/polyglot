# frozen_string_literal: true
# polyglot-covers: ruby.values.equality-identity-and-case-equality

require "assertions"

A = PolyglotAssertions

A.case("value equality, eql? and object identity answer different questions") do
  left = "ruby"
  right = +"ruby"
  A.truth(left == right)
  A.truth(left.eql?(right))
  A.falsey(left.equal?(right))
  A.truth(1 == 1.0)
  A.falsey(1.eql?(1.0))
end

A.case("Hash keys combine eql? with hash rather than numeric ==") do
  left = "ruby"
  right = +"ruby"
  mapping = {1 => :integer, 1.0 => :float, left => :text}

  A.equal(3, mapping.size)
  A.equal(:text, mapping[right])
  A.equal(left.hash, right.hash)
end

A.case("case delegates matching to each when-clause receiver through ===") do
  A.truth((1..5) === 3)
  A.truth(Integer === 42)
  A.truth(/uby/ === "ruby")
  A.equal(:integer, case 42
                    when String then :string
                    when Integer then :integer
                    end)
end

A.done
