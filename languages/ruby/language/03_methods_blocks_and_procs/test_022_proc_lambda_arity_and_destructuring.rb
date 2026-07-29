# frozen_string_literal: true
# polyglot-covers: ruby.calls.proc-lambda-arity-and-destructuring

require "assertions"

A = PolyglotAssertions

loose = proc { |left, right| [left, right] }
strict = ->(left, right) { [left, right] }
destructure = proc { |(left, right)| left + right }

A.equal([1, nil], loose.call(1))
A.equal([1, 2], loose.call(1, 2, 3))
A.raises(ArgumentError) { strict.call(1) }
A.raises(ArgumentError) { strict.call(1, 2, 3) }
A.equal([1, 2], strict.call(1, 2))
A.equal(3, destructure.call([1, 2]))
A.equal(2, strict.arity)
A.equal(2, loose.arity)
A.truth(strict.lambda?)
A.falsey(loose.lambda?)

A.done
