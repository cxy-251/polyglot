# frozen_string_literal: true
# polyglot-covers: ruby.errors.rescue-else-ensure-order

require "assertions"

A = PolyglotAssertions

events = []
result = begin
  events << :body
  42
rescue StandardError
  events << :rescue
else
  events << :else
  :success
ensure
  events << :ensure
end
A.equal(:success, result)
A.equal(%i[body else ensure], events)

attempts = 0
events = []
result = begin
  attempts += 1
  events << [:attempt, attempts]
  raise IOError, "transient" if attempts < 3

  :success
rescue IOError
  events << :rescue
  retry
ensure
  events << :ensure
end
A.equal(:success, result)
A.equal(3, attempts)
# retry 重启 begin 主体；ensure 只在最终离开整个表达式时执行一次。
A.equal([[:attempt, 1], :rescue, [:attempt, 2], :rescue, [:attempt, 3], :ensure], events)

A.done
