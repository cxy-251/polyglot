# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.definition-and-inheritance-hooks

require "assertions"

A = PolyglotAssertions

hooked_class = Class.new do
  class << self
    attr_reader :added, :children

    def method_added(name)
      (@added ||= []) << name
    end

    def inherited(child)
      (@children ||= []) << child
    end
  end

  def first
    :first
  end
end

child = Class.new(hooked_class)
A.includes(hooked_class.added, :first)
A.same(child, hooked_class.children.last)

events = []
feature = Module.new do
  define_singleton_method(:included) { |host| events << [:included, host] }
  define_singleton_method(:prepended) { |host| events << [:prepended, host] }
end
host = Class.new
host.include(feature)
host.prepend(feature)
A.equal([[:included, host], [:prepended, host]], events)

A.done
