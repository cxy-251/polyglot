# frozen_string_literal: true
# polyglot-covers: ruby.scope.assignment-changes-name-resolution

require "assertions"

A = PolyglotAssertions

receiver = Object.new
def receiver.token = :method

A.equal(:method, receiver.instance_eval { token })

result = receiver.instance_eval do
  observed_before_assignment = defined?(token)
  token = :local
  [observed_before_assignment, token, self.token]
end

A.equal(["method", :local, :method], result)

A.done
