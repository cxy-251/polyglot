# frozen_string_literal: true
# polyglot-covers: ruby.runtime.gc-state-statistics-and-restore

require "assertions"

A = PolyglotAssertions

was_disabled = GC.disable
GC.enable

begin
  before = GC.stat
  objects = 100.times.map { Object.new }
  A.equal(100, objects.length)
  A.includes(before.keys, :count)
  A.includes(before.keys, :heap_live_slots)
  A.truth(before[:count].is_a?(Integer))
  A.truth(before[:heap_live_slots].is_a?(Integer))
  GC.start(full_mark: true, immediate_sweep: true)
  after = GC.stat
  A.truth(after[:count] >= before[:count])
ensure
  was_disabled ? GC.disable : GC.enable
end

A.done
