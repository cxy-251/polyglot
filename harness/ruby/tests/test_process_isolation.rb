# frozen_string_literal: true

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.nil_value(ENV["RUBYOPT"])
A.nil_value(ENV["RUBYLIB"])

stdout, stderr, status = H.ruby_command(
  "-e",
  "ENV['POLYGLOT_CHILD_ONLY']='yes'; Object.const_set(:ChildOnly, 42); print ChildOnly"
)
A.truth(status.success?, stderr)
A.equal("42", stdout)
A.nil_value(ENV["POLYGLOT_CHILD_ONLY"])
A.falsey(Object.const_defined?(:ChildOnly, false))

fixture = H.temporary_path("isolated-feature")
FileUtils.mkdir_p(fixture)
feature = File.join(fixture, "polyglot_feature.rb")
File.write(feature, "POLYGLOT_FEATURE_VALUE = 42\n")
stdout, stderr, status = H.ruby_command(
  "-I",
  fixture,
  "-e",
  "require 'polyglot_feature'; print [POLYGLOT_FEATURE_VALUE, $LOADED_FEATURES.last].join('|')"
)
A.truth(status.success?, stderr)
A.equal("42|#{feature}", stdout)
A.falsey(Object.const_defined?(:POLYGLOT_FEATURE_VALUE, false))
A.falsey($LOADED_FEATURES.include?(feature))

A.done
