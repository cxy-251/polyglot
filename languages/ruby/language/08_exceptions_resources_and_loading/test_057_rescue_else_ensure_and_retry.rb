# frozen_string_literal: true
# polyglot-covers: ruby.errors.rescue-else-ensure-order

require "assertions"

A = PolyglotAssertions

A.case("else runs only after a successful body and ensure runs on expression exit") do
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
end

A.case("retry restarts the begin body while ensure runs once on final exit") do
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
  A.equal([[:attempt, 1], :rescue, [:attempt, 2], :rescue, [:attempt, 3], :ensure], events)
end

A.done
