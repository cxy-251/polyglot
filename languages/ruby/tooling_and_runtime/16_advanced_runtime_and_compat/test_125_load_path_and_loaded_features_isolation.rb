# frozen_string_literal: true
# polyglot-covers: ruby.runtime.load-path-and-loaded-features-isolation

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

fixture = H.temporary_path("feature")
FileUtils.mkdir_p(fixture)
feature = File.join(fixture, "polyglot_feature.rb")
File.write(feature, "POLYGLOT_FEATURE_VALUE = 42\n")

code = "require 'polyglot_feature'; print [POLYGLOT_FEATURE_VALUE, $LOADED_FEATURES.last].join('|')"
stdout, stderr, status = H.ruby_command("-I", fixture, "-e", code)
A.truth(status.success?, stderr)
value, loaded = stdout.split("|", 2)
A.equal("42", value)
A.equal(feature, loaded)
A.falsey(Object.const_defined?(:POLYGLOT_FEATURE_VALUE, false))
A.falsey($LOADED_FEATURES.include?(feature))

A.done
