# frozen_string_literal: true
# polyglot-covers: ruby.objects.include-prepend-and-ancestor-order

require "assertions"

A = PolyglotAssertions

included_feature = Module.new do
  def label
    "included"
  end
end

prepended_feature = Module.new do
  def label
    "prepended(#{super})"
  end
end

host = Class.new do
  include included_feature
  prepend prepended_feature

  def label
    "class"
  end
end

ancestors = host.ancestors
A.equal("prepended(class)", host.new.label)
A.same(prepended_feature, ancestors[0])
A.same(host, ancestors[1])
A.same(included_feature, ancestors[2])
A.falsey(host.instance_methods(false).include?(:feature))

A.done
