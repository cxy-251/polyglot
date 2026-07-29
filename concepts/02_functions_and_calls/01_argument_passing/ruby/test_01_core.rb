# 共同问题：位置参数、默认值、rest、关键字和 block 怎样绑定。
# 输入：缺省参数、额外位置参数、未知关键字和匿名 block；观察：严格 arity、关键字分离及显式转发。
# polyglot-family: functions_and_calls
# polyglot-concept: argument_passing
# polyglot-related: languages/ruby/language/03_methods_blocks_and_procs/
# polyglot-related+: test_017_positional_default_and_rest_arguments.rb

require "assertions"

A = PolyglotAssertions

def ruby_arguments(first, second = 2, *rest, required:, **extra, &block)
  [first, second, rest, required, extra, block&.call(first)]
end

A.equal([1, 2, [], 3, {}, nil], ruby_arguments(1, required: 3))
A.equal([1, 4, [5], 3, {flag: true}, 2], ruby_arguments(1, 4, 5, required: 3, flag: true) { _1 * 2 })
A.raises(ArgumentError) { ruby_arguments(required: 1) }

def exact_keyword(known:) = known
A.raises(ArgumentError) { exact_keyword(known: 1, unknown: 2) }

A.done
