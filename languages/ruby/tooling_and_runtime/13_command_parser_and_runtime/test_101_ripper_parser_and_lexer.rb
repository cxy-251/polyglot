# frozen_string_literal: true
# polyglot-covers: ruby.tooling.ripper-parser-and-lexer

require "assertions"
require "ripper"

A = PolyglotAssertions

A.case("Ripper.sexp exposes a structural parse and returns nil for invalid syntax") do
  source = "answer = 40 + 2\n"
  syntax_tree = Ripper.sexp(source)
  A.equal(:program, syntax_tree.first)
  A.truth(syntax_tree.flatten.include?(:assign))
  A.truth(syntax_tree.flatten.include?(:binary))
  A.nil_value(Ripper.sexp("def broken"))
end

A.case("Ripper.lex preserves token events and source spellings") do
  tokens = Ripper.lex("answer = 40 + 2\n")
  A.truth(tokens.any? { |_position, event, token| event == :on_ident && token == "answer" })
  A.truth(tokens.any? { |_position, event, token| event == :on_op && token == "+" })
end

A.done
