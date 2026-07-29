# frozen_string_literal: true
# polyglot-covers: ruby.runtime.gc-state-statistics-and-restore

require "assertions"

A = PolyglotAssertions

was_disabled = GC.disable
GC.enable
begin
  before = GC.stat
  objects = 50.times.map { |index| "value-#{index}" }
  A.includes(before.keys, :count)
  A.includes(before.keys, :heap_live_slots)
  A.truth(before[:count].is_a?(Integer))

  GC.start(full_mark: true, immediate_sweep: true)
  after = GC.stat
  A.truth(after[:count] >= before[:count])

  # compact 的统计形状和移动策略属于锁定 CRuby 观察；对象引用保持有效才是 API 边界。
  if GC.respond_to?(:compact)
    compact_result = GC.compact
    A.truth(compact_result.is_a?(Hash))
    A.equal("value-0", objects.first)
    A.equal("value-49", objects.last)
  end
ensure
  was_disabled ? GC.disable : GC.enable
end

A.done
