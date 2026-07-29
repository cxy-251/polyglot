# frozen_string_literal: true
# polyglot-covers: ruby.scope.autoload-and-top-level-context

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

fixture = H.temporary_path("autoload_fixture.rb")
File.write(fixture, "module AutoloadFixture\n  VALUE = 42\nend\n")

namespace = Module.new
Object.const_set(:AutoloadFixture, namespace)
namespace.autoload(:VALUE, fixture)

A.equal(fixture, namespace.autoload?(:VALUE))
A.equal(42, namespace::VALUE)
A.nil_value(namespace.autoload?(:VALUE))
A.truth(self.is_a?(Object))
A.same(self, TOPLEVEL_BINDING.receiver)
A.equal(__FILE__, $PROGRAM_NAME)

A.done
