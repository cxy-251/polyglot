# frozen_string_literal: true
# polyglot-covers: ruby.loading.require-load-and-feature-cache

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

fixture = H.temporary_path("feature.rb")
File.write(fixture, <<~RUBY)
  $polyglot_feature_count ||= 0
  $polyglot_feature_count += 1
RUBY

A.truth(require(fixture))
A.equal(1, $polyglot_feature_count)
A.falsey(require(fixture))
A.equal(1, $polyglot_feature_count)
A.truth(load(fixture))
A.equal(2, $polyglot_feature_count)
A.includes($LOADED_FEATURES, fixture)

A.done
