# frozen_string_literal: true
# polyglot-covers: ruby.runtime.finalizer-registration-without-timing-assumption

require "assertions"

A = PolyglotAssertions

events = []
object = Object.new
finalizer = proc { |object_id| events << object_id }
returned = ObjectSpace.define_finalizer(object, finalizer)

A.equal([0, finalizer], returned)
A.equal([], events)
A.same(object, ObjectSpace.undefine_finalizer(object))
A.equal([], events)

# 不断言 finalizer 的执行时间或顺序；这里只验证注册与显式撤销的稳定接口。
A.truth(object.object_id.positive?)

A.done
