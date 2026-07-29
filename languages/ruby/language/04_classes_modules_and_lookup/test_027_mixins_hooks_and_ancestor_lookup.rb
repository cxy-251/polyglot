# frozen_string_literal: true
# polyglot-covers: ruby.objects.include-prepend-and-ancestor-order

require "assertions"

A = PolyglotAssertions

events = []
included_feature = Module.new do
  define_singleton_method(:included) { |host| events << [:included, host] }

  def label
    "included"
  end
end
prepended_feature = Module.new do
  define_singleton_method(:prepended) { |host| events << [:prepended, host] }

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

A.equal([[:included, host], [:prepended, host]], events)
A.equal("prepended(class)", host.new.label)
A.equal([prepended_feature, host, included_feature], host.ancestors.take(3))
A.truth(included_feature.instance_methods(false).include?(:label))
A.truth(prepended_feature.instance_methods(false).include?(:label))

A.done
