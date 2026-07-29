# frozen_string_literal: true
# polyglot-covers: ruby.collections.external-enumerator-state

require "assertions"

A = PolyglotAssertions

enumerator = %i[first second].each
A.equal(:first, enumerator.peek)
A.equal(:first, enumerator.next)
A.equal(:second, enumerator.next)
error = A.raises(StopIteration) { enumerator.next }
A.equal(%i[first second], error.result)
enumerator.rewind
A.equal(:first, enumerator.next)

produced = Enumerator.new do |output|
  output << 10
  output.yield(20)
end
A.equal([10, 20], produced.to_a)

A.done
