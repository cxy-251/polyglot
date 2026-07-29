# frozen_string_literal: true
# polyglot-covers: ruby.loading.require-load-and-feature-cache

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

fixture = H.temporary_path("feature.rb")
File.write(fixture, "$polyglot_feature_count = ($polyglot_feature_count || 0) + 1\n")
A.truth(require(fixture))
A.equal(1, $polyglot_feature_count)
A.falsey(require(fixture))
A.equal(1, $polyglot_feature_count)
A.truth(load(fixture))
A.equal(2, $polyglot_feature_count)
A.includes($LOADED_FEATURES, fixture)

failing = H.temporary_path("failing_feature.rb")
File.write(
  failing,
  "$polyglot_failed_count = ($polyglot_failed_count || 0) + 1\nraise 'load failed'\n"
)
2.times { A.raises(RuntimeError, "load failed") { require(failing) } }
# 执行失败的 feature 不进入缓存，下一次 require 会重新执行。
A.equal(2, $polyglot_failed_count)
A.falsey($LOADED_FEATURES.include?(failing))

autoload_file = H.temporary_path("autoload_value.rb")
File.write(autoload_file, "module AutoloadNamespace\n  VALUE = 42\nend\n")
module AutoloadNamespace
end
AutoloadNamespace.autoload(:VALUE, autoload_file)
A.equal(autoload_file, AutoloadNamespace.autoload?(:VALUE))
A.equal(42, AutoloadNamespace::VALUE)
A.nil_value(AutoloadNamespace.autoload?(:VALUE))

A.done
