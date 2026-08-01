# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.binding-eval-and-local-variables

require "assertions"

A = PolyglotAssertions

A.case("eval resolves names through the supplied Binding") do
  value = 10
  captured = binding
  A.equal(15, eval("value + 5", captured))
  A.equal(10, value)
  A.equal(10, captured.local_variable_get(:value))
end

A.case("Binding local-variable APIs update captured slots and can add dynamic slots") do
  value = 10
  captured = binding
  captured.local_variable_set(:value, 20)
  captured.local_variable_set(:created, :dynamic)

  A.equal(20, value)
  A.equal(:dynamic, captured.local_variable_get(:created))
  A.includes(captured.local_variables, :created)
end

A.case("eval parses its source before execution and reports invalid syntax") do
  A.raises(SyntaxError) { eval("def", binding) }
end

A.done
