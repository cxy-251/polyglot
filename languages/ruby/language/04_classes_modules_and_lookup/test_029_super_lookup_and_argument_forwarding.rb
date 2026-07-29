# frozen_string_literal: true
# polyglot-covers: ruby.objects.super-lookup-and-argument-forwarding

require "assertions"

A = PolyglotAssertions

super_base = Class.new do
  def describe(value, suffix: "base")
    "#{value}:#{suffix}"
  end
end

super_child = Class.new(super_base) do
  def describe(value, suffix: "child")
    "child(#{super})"
  end
end

explicit_child = Class.new(super_base) do
  def describe(_value, suffix: "ignored")
    super("fixed", suffix: suffix.upcase)
  end
end

A.equal("child(item:child)", super_child.new.describe("item"))
A.equal("fixed:CUSTOM", explicit_child.new.describe("item", suffix: "custom"))
A.same(super_child, super_child.instance_method(:describe).owner)
A.same(super_base, super_base.instance_method(:describe).owner)

A.done
