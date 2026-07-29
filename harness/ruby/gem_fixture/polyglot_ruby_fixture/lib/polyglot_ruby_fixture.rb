# frozen_string_literal: true
# Repository-local harness fixture library.

require_relative "polyglot_ruby_fixture/version"

module PolyglotRubyFixture
  module_function

  def label(value)
    "ruby:#{value}"
  end
end
