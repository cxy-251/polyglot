// polyglot-covers:
// - cpp.stdlib.io.osyncstream-deferred-emission-and-destruction
// - cpp.stdlib.io.osyncstream-emit-and-wrapped-buffer
// - cpp.stdlib.io.syncbuf-direct-use-emit-and-set-emit-on-sync
// - cpp.stdlib.io.emit-on-flush-noemit-on-flush-and-flush-emit
// - cpp.stdlib.io.osyncstream-move-and-buffer-ownership
// - cpp.stdlib.io.osyncstream-emission-order-and-noninterleaved-chunks
// - cpp.stdlib.io.syncstream-wrapped-lifetime-and-failure-contract
// - cpp.stdlib.io.locked-libstdcxx-syncstream-feature-detection

#include <gtest/gtest.h>

#include <ostream>
#include <sstream>
#include <string>
#include <syncstream>
#include <utility>

namespace {

#if defined(__cpp_lib_syncbuf) && __cpp_lib_syncbuf >= 201803L

TEST(SynchronizedOutput, CharactersStayPrivateUntilEmitOrDestruction) {
  std::ostringstream sink;
  {
    std::osyncstream output{sink};
    output << "deferred";
    EXPECT_EQ(sink.str(), "");

    output.emit();
    EXPECT_EQ(sink.str(), "deferred");
    output << "+tail";
    EXPECT_EQ(sink.str(), "deferred");
  }
  EXPECT_EQ(sink.str(), "deferred+tail");

  // osyncstream 先写入自有 syncbuf，emit 或析构才把一整块提交给 wrapped buffer。
  // 原子性针对共享同一最终 streambuf 的同步缓冲区，不等于每个 << 立即可见。
}

TEST(SynchronizedOutput, GetWrappedExposesTheNonOwnedDestinationBuffer) {
  std::ostringstream sink;
  std::osyncstream output{sink};

  EXPECT_EQ(output.get_wrapped(), sink.rdbuf());
  output << "text";
  output.emit();
  EXPECT_EQ(sink.str(), "text");

  // get_wrapped 返回借用指针；osyncstream 不拥有 sink。目标必须比所有同步流及其
  // 最终 emit 活得更久，也不能在并发写入期间无同步地替换 rdbuf。
}

TEST(Syncbuf, DirectBufferUseSeparatesStreamFormattingFromChunkEmission) {
  std::ostringstream sink;
  std::syncbuf buffer{sink.rdbuf()};
  std::ostream output{&buffer};

  output << "one";
  EXPECT_EQ(sink.str(), "");
  EXPECT_TRUE(buffer.emit());
  EXPECT_EQ(sink.str(), "one");

  buffer.set_emit_on_sync(true);
  output << "+two" << std::flush;
  EXPECT_EQ(sink.str(), "one+two");

  // syncbuf::emit 返回提交是否成功；set_emit_on_sync(true) 让 pubsync/flush 同时
  // 触发 emit。普通 syncbuf 默认 sync 只记录同步请求，不必立刻公开字符。
}

TEST(SyncstreamManipulators, FlushAndEmissionCanBeControlledIndependently) {
  std::ostringstream sink;
  {
    std::osyncstream output{sink};
    output << std::noemit_on_flush << "A" << std::flush;
    EXPECT_EQ(sink.str(), "");

    output << std::flush_emit;
    EXPECT_EQ(sink.str(), "A");

    output << std::emit_on_flush << "B" << std::flush;
    EXPECT_EQ(sink.str(), "AB");

    output << std::noemit_on_flush << "C" << std::endl;
    EXPECT_EQ(sink.str(), "AB");
  }
  EXPECT_EQ(sink.str(), "ABC\n");

  // flush_emit 同步并提交；emit_on_flush/noemit_on_flush 改变后续 flush 行为。
  // endl 仍只是“换行+flush”，若关闭 emit-on-flush，块要到显式 emit/析构才可见。
}

TEST(SynchronizedOutput, MoveTransfersThePendingChunkAndOnlyTheDestinationEmitsIt) {
  std::ostringstream sink;
  {
    std::osyncstream source{sink};
    source << "before";
    std::osyncstream destination{std::move(source)};
    destination << "+after";
  }

  EXPECT_EQ(sink.str(), "before+after");

  // 移动转移 wrapped 指针、allocator 和待提交字符；移动源保持可析构，但不再
  // 拥有该块。不要在移动后继续依赖源的格式状态或 get_wrapped 结果。
}

TEST(SynchronizedOutput, WholeChunksFollowEmissionOrderRatherThanInsertionOrder) {
  std::ostringstream sink;
  std::osyncstream first{sink};
  std::osyncstream second{sink};

  first << "[first:1,2]";
  second << "[second:a,b]";
  EXPECT_EQ(sink.str(), "");

  second.emit();
  first.emit();
  EXPECT_EQ(sink.str(), "[second:a,b][first:1,2]");

  // 同步流保证各块不互相穿插，不保证创建顺序或 << 时间顺序；真正顺序由 emit/
  // 析构取得内部锁的先后决定。日志若需要全序，还必须携带序号或外部同步。
}

#else

TEST(SynchronizedOutput, LockedLibstdcxxGapPreservesTheCxx20SyncstreamWorkflow) {
  GTEST_SKIP()
      << "The locked standard library does not expose __cpp_lib_syncbuf; "
         "the feature branch retains deferred emission, manipulators, moves, and chunks";
}

#endif

}  // namespace
