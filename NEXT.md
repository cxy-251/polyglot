# Current Task

ID: `python.stdlib.collections-deque-ordereddict`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.deque` 与 `OrderedDict` 测试套，覆盖双端队列、固定容量窗口、rotate/recipe 和显式顺序重排语义；说明普通 dict 已保留插入顺序后，OrderedDict 仍在 FIFO/LIFO pop、移动到任一端和 order-sensitive 同类比较方面的价值。

## Covers

- `deque(iterable, maxlen=None)` 左到右构造、`maxlen` 只读属性；
- `append()` / `appendleft()` / `pop()` / `popleft()` 的双端 O(1) 工作流；
- `extend()` 保持输入顺序，`extendleft()` 因逐项左插而反转输入顺序；
- bounded deque 满载后从相反一端自动丢弃旧元素；
- `maxlen=0` 吞掉所有 append，适合只消费 iterable 的特殊边界；
- 满载 bounded deque 的 `insert()` 不会淘汰而是抛 `IndexError`；
- `rotate(n)` 正数向右、负数向左，步数按长度循环；
- `reverse()` 原地返回 `None`，`reversed()` 提供反向 iterator；
- `copy()` 是浅复制并保留 maxlen；
- `count()` / `index(start, stop)` / `remove()` / `clear()`；
- 端点索引、负索引和中间随机访问；明确 deque 不支持 slicing 且中间索引不是 list 的性能替代；
- `+` / `*` / `*=` 的序列组合行为和 bounded maxlen 截断；
- 空 deque pop/popleft 与缺失 index/remove 的异常边界；
- bounded deque 实现 tail/recent-history，deque 实现 moving-window/round-robin 的可读 recipe；
- append/pop 双端操作是 thread-safe，但组合检查+操作不是原子事务；不写时序脆弱线程测试；
- `OrderedDict` 构造和覆盖已有 key 不自动改变原位置；
- `move_to_end(key, last=True/False)` 移至右端或左端；
- `popitem(last=True)` LIFO 与 `popitem(last=False)` FIFO；
- `reversed(od)` 以及 keys/items/values view 的反向迭代；
- 两个 OrderedDict 之间 equality 对顺序敏感；与普通 Mapping 比较时对顺序不敏感；
- `|` / `|=` 合并时的类型、值和 key 顺序；
- 最后更新顺序 subclass 与小型 LRU 工作流，说明何时普通 dict 不足；
- 空 popitem、移动缺失 key 的 `KeyError`。

## Common Pitfalls To Explain

- 认为 `extendleft([1,2,3])` 得到从左到右 1,2,3；
- 满载 bounded deque 使用 `insert()` 时期待像 append 一样自动淘汰；
- 把 deque 当支持 slicing/快速中间随机访问的 list；
- 忘记 maxlen eviction 的方向取决于从哪一端添加；
- 把 rotate 的正负方向写反；
- 看到单个 deque 操作 thread-safe 就推断多步业务流程自动原子；
- 只因需要 insertion order 就选择 OrderedDict；现代 dict 已保证该顺序；
- 覆盖 OrderedDict 已有 key 后以为它自动移动到末尾；
- 忘记 OrderedDict 对同类比较时顺序会参与 equality；
- 用普通 dict 模拟 `move_to_end(last=False)` 写出昂贵/难读代码。

## Target File

`languages/python/stdlib/data_types/test_047_deque_ordereddict.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.html#deque-objects
- https://docs.python.org/3.10/library/collections.html#ordereddict-objects

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- recipe 保持小型、确定性，不使用 sleep 或时钟；
- 不用并发压力测试证明文档的 thread-safe 单操作保证，只用注释划清组合操作边界；
- OrderedDict 案例必须展示普通 dict 无法同样简洁表达的重排/FIFO 能力；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--045 已完成此前范围首轮编写；046 `Counter` / `defaultdict` 已在 `data_types/` 完成首轮静态编写，覆盖 Python 3.10 total/comparisons 与 missing factory 副作用。全部 Python 文件仍未运行。下一步直接编写 047 `deque` / `OrderedDict`；不要先运行 pytest。
