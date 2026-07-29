# frozen_string_literal: true
# polyglot-covers: ruby.objects.alias-remove-and-undef-method

require "assertions"

A = PolyglotAssertions

base = Class.new do
  def value
    :base
  end
end

aliasing = Class.new(base) do
  alias_method :original_value, :value

  def value
    :child
  end
end

removing = Class.new(aliasing) do
  def value
    :temporary
  end

  remove_method :value
end

undefining = Class.new(base) do
  undef_method :value
end

A.equal(:child, aliasing.new.value)
A.equal(:base, aliasing.new.original_value)
A.equal(:child, removing.new.value)
A.raises(NoMethodError) { undefining.new.value }
A.falsey(undefining.method_defined?(:value))

A.done
