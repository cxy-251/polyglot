# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.binding-eval-and-local-variables

require "assertions"

A = PolyglotAssertions

value = 10
captured = binding
A.equal(15, eval("value + 5", captured))
A.equal(10, captured.local_variable_get(:value))
captured.local_variable_set(:value, 20)
A.equal(20, value)
captured.local_variable_set(:created, :dynamic)
A.equal(:dynamic, captured.local_variable_get(:created))
A.includes(captured.local_variables, :created)
A.raises(SyntaxError) { eval("def", captured) }

A.done
