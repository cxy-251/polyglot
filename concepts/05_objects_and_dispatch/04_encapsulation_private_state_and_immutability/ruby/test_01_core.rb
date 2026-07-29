# 共同问题：私有状态、方法可见性和不可变性怎样表达。
# 输入：private reader、public_send、send、freeze 及嵌套对象；观察：可见性检查、反射绕过和浅冻结。
# polyglot-family: objects_and_dispatch
# polyglot-concept: encapsulation_private_state_and_immutability
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/
# polyglot-related+: test_028_visibility_dynamic_fallback_and_reflection.rb

require "assertions"

A = PolyglotAssertions

vault_class = Class.new do
  def initialize(secret) = @secret = secret
  def reveal = secret

  private

  attr_reader :secret
end

vault = vault_class.new("ruby")
A.equal("ruby", vault.reveal)
A.falsey(vault.respond_to?(:secret))
A.truth(vault.respond_to?(:secret, true))
A.raises(NoMethodError) { vault.public_send(:secret) }
A.equal("ruby", vault.send(:secret))

nested = [+"mutable"].freeze
A.raises(FrozenError) { nested << "new" }
nested.first << "-inside"
A.equal("mutable-inside", nested.first)

A.done
