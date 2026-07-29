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

events = []
result = begin
  raise ArgumentError, "bad"
rescue ArgumentError => error
  events << error.class
  :rescued
ensure
  events << :ensure
end
A.equal(:rescued, result)
A.equal([ArgumentError, :ensure], events)

A.done
