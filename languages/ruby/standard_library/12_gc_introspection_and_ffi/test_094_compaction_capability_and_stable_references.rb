# frozen_string_literal: true
# polyglot-covers: ruby.runtime.compaction-capability-and-stable-references

require "assertions"

A = PolyglotAssertions

objects = 50.times.map { |index| "value-#{index}" }
A.truth(GC.respond_to?(:compact))
A.truth(GC.respond_to?(:latest_compact_info))

result = GC.compact
A.truth(result.is_a?(Hash))
A.includes(result.keys, :considered)
A.includes(result.keys, :moved)
A.equal("value-0", objects.first)
A.equal("value-49", objects.last)

information = GC.latest_compact_info
A.truth(information.is_a?(Hash))
A.includes(information.keys, :considered)
A.includes(information.keys, :moved)

A.done
