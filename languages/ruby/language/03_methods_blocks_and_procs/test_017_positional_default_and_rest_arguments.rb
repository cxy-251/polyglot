# frozen_string_literal: true
# polyglot-covers: ruby.calls.positional-default-and-rest-arguments

require "assertions"

A = PolyglotAssertions

def collect_arguments(first, second = 2, *rest)
  [first, second, rest]
end

A.equal([1, 2, []], collect_arguments(1))
A.equal([1, 3, [4, 5]], collect_arguments(1, 3, 4, 5))
A.equal([1, {key: true}, []], collect_arguments(1, key: true))
A.raises(ArgumentError) { collect_arguments }

parameters = method(:collect_arguments).parameters
A.equal([[:req, :first], [:opt, :second], [:rest, :rest]], parameters)

A.done
