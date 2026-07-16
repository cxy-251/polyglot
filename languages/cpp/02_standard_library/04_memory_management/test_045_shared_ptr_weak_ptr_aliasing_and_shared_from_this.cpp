// polyglot-covers:
// - cpp.stdlib.memory.shared-ptr-control-block-and-use-count
// - cpp.stdlib.memory.make-shared
// - cpp.stdlib.memory.weak-ptr-lock-and-expiration
// - cpp.stdlib.memory.shared-ptr-aliasing-constructor
// - cpp.stdlib.memory.shared-ptr-owner-ordering
// - cpp.stdlib.memory.enable-shared-from-this
// - cpp.stdlib.memory.shared-ptr-pointer-casts
// - cpp.stdlib.memory.shared-ptr-custom-deleter
// - cpp.stdlib.memory.weak-ptr-breaks-ownership-cycles
// - cpp.stdlib.memory.allocate-shared

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <memory>
#include <memory_resource>
#include <string>
#include <utility>

namespace {

struct SharedTracked {
  static inline int live_count = 0;

  explicit SharedTracked(int value) : value(value) { ++live_count; }
  virtual ~SharedTracked() { --live_count; }

  int value;
};

struct PairOwner {
  int first;
  int second;
};

class SelfAware : public std::enable_shared_from_this<SelfAware> {
 public:
  explicit SelfAware(int id) : id_(id) {}

  std::shared_ptr<SelfAware> share() { return shared_from_this(); }
  std::weak_ptr<SelfAware> observe() noexcept { return weak_from_this(); }
  int id() const { return id_; }

 private:
  int id_;
};

struct CastBase {
  virtual ~CastBase() = default;
};

struct CastDerived : CastBase {
  int value = 27;
};

struct CountingDeleter {
  int* calls;

  void operator()(SharedTracked* pointer) const noexcept {
    ++*calls;
    delete pointer;
  }
};

struct GraphNode {
  static inline int live_count = 0;

  explicit GraphNode(std::string name) : name(std::move(name)) { ++live_count; }
  ~GraphNode() { --live_count; }

  std::string name;
  std::shared_ptr<GraphNode> child;
  std::weak_ptr<GraphNode> parent;
};

TEST(SharedPtr, CopiesShareAControlBlockAndDestroyAtTheLastStrongOwner) {
  SharedTracked::live_count = 0;
  std::weak_ptr<SharedTracked> observer;

  {
    auto first = std::make_shared<SharedTracked>(5);
    observer = first;
    EXPECT_EQ(first.use_count(), 1);

    auto second = first;
    EXPECT_EQ(first.use_count(), 2);
    EXPECT_EQ(second.get(), first.get());
    EXPECT_EQ(SharedTracked::live_count, 1);
  }

  EXPECT_TRUE(observer.expired());
  EXPECT_EQ(SharedTracked::live_count, 0);

  // shared_ptr 副本共享 control block 的强计数；最后一个强 owner 销毁对象。weak_ptr 保留
  // control block 的观察状态却不延长对象寿命，use_count 只适合诊断，不能用于同步决策。
}

TEST(WeakPtr, LockAtomicallyProducesAnOwnerOrAnEmptyPointer) {
  auto owner = std::make_shared<int>(42);
  std::weak_ptr<int> observer = owner;

  auto locked = observer.lock();
  ASSERT_NE(locked, nullptr);
  EXPECT_EQ(*locked, 42);

  owner.reset();
  EXPECT_FALSE(observer.expired());
  locked.reset();
  EXPECT_TRUE(observer.expired());
  EXPECT_EQ(observer.lock(), nullptr);

  // lock 在并发语义上以一个操作完成“检查仍存活并增加强计数”；先 expired() 再构造 owner
  // 会有竞态。这里第一次 lock 自己也成为 owner，所以原 owner reset 后对象仍存活。
}

TEST(SharedPtrAliasing, StoredPointerMayDifferFromTheOwnedObjectPointer) {
  auto pair = std::make_shared<PairOwner>(PairOwner{3, 9});
  std::shared_ptr<int> second{pair, &pair->second};

  EXPECT_EQ(second.get(), &pair->second);
  EXPECT_EQ(*second, 9);
  EXPECT_EQ(second.use_count(), 2);
  EXPECT_FALSE(pair.owner_before(second));
  EXPECT_FALSE(second.owner_before(pair));

  pair.reset();
  EXPECT_EQ(*second, 9);

  // aliasing constructor 共享 pair 的 control block，却让 get() 指向成员。owner_before 比较
  // 所有权身份而非存储指针；只要 alias owner 存活，完整 PairOwner 对象也继续存活。
}

TEST(EnableSharedFromThis, ReusesTheExistingControlBlock) {
  auto owner = std::make_shared<SelfAware>(17);
  auto from_this = owner->share();

  EXPECT_EQ(from_this.get(), owner.get());
  EXPECT_EQ(owner.use_count(), 2);
  EXPECT_EQ(from_this->id(), 17);
  EXPECT_FALSE(owner.owner_before(from_this));
  EXPECT_FALSE(from_this.owner_before(owner));

  // shared_from_this 从 make_shared 初始化的内部 weak owner 创建新副本，不能用
  // shared_ptr<T>(this) 替代，后者会建立第二个 control block 并最终 double delete。
}

TEST(EnableSharedFromThis, UnmanagedObjectCannotInventSharedOwnership) {
  SelfAware local{8};

  EXPECT_THROW((void)local.share(), std::bad_weak_ptr);
  EXPECT_TRUE(local.observe().expired());

  // 对尚未由兼容 shared_ptr 管理的对象，shared_from_this 抛 bad_weak_ptr；C++17 的
  // weak_from_this 则安全返回空观察者。构造函数中通常也还不能调用 shared_from_this。
}

TEST(SharedPtrCasts, CastHelpersPreserveTheControlBlock) {
  std::shared_ptr<CastBase> base = std::make_shared<CastDerived>();
  auto derived = std::dynamic_pointer_cast<CastDerived>(base);

  ASSERT_NE(derived, nullptr);
  EXPECT_EQ(derived->value, 27);
  EXPECT_EQ(base.use_count(), 2);

  struct Other : CastBase {};
  auto failed = std::dynamic_pointer_cast<Other>(base);
  EXPECT_EQ(failed, nullptr);

  // pointer_cast helpers 对 stored pointer 做对应 cast，同时复用原 control block。失败的
  // dynamic_pointer_cast 返回空 shared_ptr，不增加计数；static 版本不做运行期类型检查。
}

TEST(SharedPtr, CustomDeleterLivesInTheControlBlockAndCanBeInspected) {
  SharedTracked::live_count = 0;
  int delete_calls = 0;

  {
    std::shared_ptr<SharedTracked> owner{
        new SharedTracked{11},
        CountingDeleter{&delete_calls},
    };
    const auto* deleter = std::get_deleter<CountingDeleter>(owner);
    ASSERT_NE(deleter, nullptr);
    EXPECT_EQ(deleter->calls, &delete_calls);
  }

  EXPECT_EQ(delete_calls, 1);
  EXPECT_EQ(SharedTracked::live_count, 0);

  // shared_ptr 的 deleter 类型不进入 shared_ptr<T> 本身类型，而是保存在 control block。
  // get_deleter 只有请求的准确类型匹配才返回指针；业务逻辑不应依赖它替代显式资源接口。
}

TEST(SharedPtr, AllocateSharedUsesTheProvidedAllocatorForOwnedState) {
  SharedTracked::live_count = 0;
  std::array<std::byte, 512> buffer{};
  std::pmr::monotonic_buffer_resource resource{
      buffer.data(),
      buffer.size(),
      std::pmr::null_memory_resource(),
  };
  std::pmr::polymorphic_allocator<SharedTracked> allocator{&resource};

  {
    auto owner = std::allocate_shared<SharedTracked>(allocator, 29);
    EXPECT_EQ(owner->value, 29);
    EXPECT_EQ(SharedTracked::live_count, 1);
  }
  EXPECT_EQ(SharedTracked::live_count, 0);

  // allocate_shared 把 allocator 用于对象及其共享状态，适合 arena/统计资源；资源必须比
  // control block 长寿。与 shared_ptr(new T, deleter) 不同，它不接收独立 custom deleter。
}

TEST(WeakPtr, ParentBackReferenceBreaksAGraphOwnershipCycle) {
  GraphNode::live_count = 0;

  {
    auto parent = std::make_shared<GraphNode>("parent");
    auto child = std::make_shared<GraphNode>("child");
    parent->child = child;
    child->parent = parent;

    ASSERT_NE(child->parent.lock(), nullptr);
    EXPECT_EQ(child->parent.lock()->name, "parent");
    EXPECT_EQ(GraphNode::live_count, 2);
  }

  EXPECT_EQ(GraphNode::live_count, 0);

  // 若 parent 和 child 两个方向都用 shared_ptr，强计数环会让二者永不归零。非拥有的
  // 回边应使用 weak_ptr，并在每次访问时 lock 后检查对象是否仍存在。
}

}  // namespace
