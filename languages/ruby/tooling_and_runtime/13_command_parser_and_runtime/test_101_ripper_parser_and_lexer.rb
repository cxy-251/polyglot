# frozen_string_literal: true
# polyglot-covers: ruby.tooling.ripper-parser-and-lexer

require "assertions"
require "ripper"

A = PolyglotAssertions

source = "answer = 40 + 2\n"
syntax_tree = Ripper.sexp(source)
A.equal(:program, syntax_tree.first)
A.truth(syntax_tree.flatten.include?(:assign))
A.truth(syntax_tree.flatten.include?(:binary))

tokens = Ripper.lex(source)
A.truth(tokens.any? { |_position, event, token| event == :on_ident && token == "answer" })
A.truth(tokens.any? { |_position, event, token| event == :on_op && token == "+" })
A.nil_value(Ripper.sexp("def broken"))

A.done
