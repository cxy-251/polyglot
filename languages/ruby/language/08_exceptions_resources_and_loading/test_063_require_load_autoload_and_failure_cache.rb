# frozen_string_literal: true
# polyglot-covers: ruby.loading.require-load-and-feature-cache

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.case("require caches a successful feature while load executes it again") do
  fixture = H.temporary_path("feature.rb")
  File.write(fixture, "$polyglot_feature_count = ($polyglot_feature_count || 0) + 1\n")
  A.truth(require(fixture))
  A.equal(1, $polyglot_feature_count)
  A.falsey(require(fixture))
  A.equal(1, $polyglot_feature_count)
  A.truth(load(fixture))
  A.equal(2, $polyglot_feature_count)
  A.includes($LOADED_FEATURES, fixture)
end

A.case("a failing require does not cache success and therefore executes again") do
  failing = H.temporary_path("failing_feature.rb")
  File.write(
    failing,
    "$polyglot_failed_count = ($polyglot_failed_count || 0) + 1\nraise 'load failed'\n"
  )
  2.times { A.raises(RuntimeError, "load failed") { require(failing) } }
  A.equal(2, $polyglot_failed_count)
  A.falsey($LOADED_FEATURES.include?(failing))
end

A.case("autoload records a pending feature and clears it after constant resolution") do
  autoload_file = H.temporary_path("autoload_value.rb")
  File.write(autoload_file, "module AutoloadNamespace\n  VALUE = 42\nend\n")
  module AutoloadNamespace
  end
  AutoloadNamespace.autoload(:VALUE, autoload_file)
  A.equal(autoload_file, AutoloadNamespace.autoload?(:VALUE))
  A.equal(42, AutoloadNamespace::VALUE)
  A.nil_value(AutoloadNamespace.autoload?(:VALUE))
end

A.done
