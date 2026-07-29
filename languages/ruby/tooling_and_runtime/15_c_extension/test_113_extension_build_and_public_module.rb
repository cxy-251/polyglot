# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.build-and-public-module

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal("CRuby 4.0.6", PolyglotNative::RELEASE)
A.truth(PolyglotNative.is_a?(Module))
A.includes(PolyglotNative.singleton_methods(false), :add)
A.includes(PolyglotNative.singleton_methods(false), :without_gvl_sum)
A.nil_value(PolyglotNative.method(:add).source_location)

A.done
