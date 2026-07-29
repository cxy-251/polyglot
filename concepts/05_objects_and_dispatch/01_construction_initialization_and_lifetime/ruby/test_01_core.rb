# 共同问题：分配、初始化、对象身份和资源生命周期怎样连接。
# 输入：Class#new、allocate、initialize、显式 close 和 block；观察：初始化调用、未初始化状态及确定性清理。
# polyglot-family: objects_and_dispatch
# polyglot-concept: construction_initialization_and_lifetime
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/
# polyglot-related+: test_025_construction_inheritance_and_super.rb

require "assertions"

A = PolyglotAssertions

resource_class = Class.new do
  attr_reader :name

  def initialize(name)
    @name = name
    @closed = false
  end

  def close = @closed = true
  def closed? = @closed
end

resource = resource_class.new("ruby")
A.equal("ruby", resource.name)
A.falsey(resource.closed?)
A.same(resource_class, resource.class)
A.falsey(resource_class.allocate.instance_variable_defined?(:@name))

begin
  A.same(resource, resource)
ensure
  resource.close
end
A.truth(resource.closed?)

A.done
