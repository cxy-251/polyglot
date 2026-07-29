# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.io-select-and-explicit-readiness

require "assertions"

A = PolyglotAssertions

reader, writer = IO.pipe
producer = Thread.new do
  writer.write("ready")
  writer.close
  :written
end

ready_readers, ready_writers = IO.select([reader], [], [], 1)
A.includes(ready_readers, reader)
A.equal([], ready_writers)
A.equal("ready", reader.read)
A.equal(:written, producer.value)
A.falsey(producer.alive?)
reader.close
A.truth(reader.closed?)

A.done
