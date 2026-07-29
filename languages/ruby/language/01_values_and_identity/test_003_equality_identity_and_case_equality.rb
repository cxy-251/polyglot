# frozen_string_literal: true
# polyglot-covers: ruby.values.equality-identity-and-case-equality

require "assertions"

A = PolyglotAssertions

left = "ruby"
right = +"ruby"
A.truth(left == right)
A.truth(left.eql?(right))
A.falsey(left.equal?(right))
A.truth((1..5) === 3)
A.truth(Integer === 42)
A.truth(/uby/ === "ruby")
A.equal(left.hash, right.hash)
A.falsey(1.eql?(1.0))
A.truth(1 == 1.0)

A.done
