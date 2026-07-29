# frozen_string_literal: true

require_relative "polyglot_ruby_fixture/version"

module PolyglotRubyFixture
  module_function

  def label(value)
    "ruby:#{value}"
  end
end
