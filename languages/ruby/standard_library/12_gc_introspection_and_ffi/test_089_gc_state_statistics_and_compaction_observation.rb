# frozen_string_literal: true
# polyglot-covers: ruby.runtime.gc-state-statistics-and-restore

require "assertions"

A = PolyglotAssertions

A.case("GC.stat exposes counters and an explicit collection advances or preserves count") do
  was_disabled = GC.disable
  GC.enable
  begin
    before = GC.stat
    A.includes(before.keys, :count)
    A.includes(before.keys, :heap_live_slots)
    A.truth(before[:count].is_a?(Integer))

    GC.start(full_mark: true, immediate_sweep: true)
    after = GC.stat
    A.truth(after[:count] >= before[:count])
  ensure
    was_disabled ? GC.disable : GC.enable
  end
end

if GC.respond_to?(:compact)
  A.case("CRuby compaction keeps live Ruby references valid") do
    was_disabled = GC.disable
    GC.enable
    objects = 50.times.map { |index| "value-#{index}" }
    compact_result = GC.compact
    A.truth(compact_result.is_a?(Hash))
    A.equal("value-0", objects.first)
    A.equal("value-49", objects.last)
  ensure
    was_disabled ? GC.disable : GC.enable
  end
else
  A.skip("CRuby compaction keeps live Ruby references valid", "GC.compact unavailable")
end

A.done
