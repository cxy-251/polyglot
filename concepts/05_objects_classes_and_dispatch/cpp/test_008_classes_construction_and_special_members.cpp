// polyglot-covers:
// - cpp.language.class-construction-and-destruction-order
// - cpp.language.explicit-and-delegating-constructors
// - cpp.language.copy-and-move-special-members
// - cpp.language.user-declared-destructor-suppresses-move
// - cpp.language.defaulted-and-deleted-special-members
// - cpp.language.rule-of-zero

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class EventPart {
 public:
  EventPart(std::vector<std::string>& events, std::string name)
      : events_(events), name_(std::move(name)) {
    events_.push_back("construct " + name_);
  }

  ~EventPart() { events_.push_back("destroy " + name_); }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

class EventBase {
 public:
  explicit EventBase(std::vector<std::string>& events)
      : part_(events, "base") {}

 private:
  EventPart part_;
};

class EventOwner : public EventBase {
 public:
  explicit EventOwner(std::vector<std::string>& events)
      : EventBase(events), first_(events, "first member"), second_(events, "second member") {}

 private:
  EventPart first_;
  EventPart second_;
};

class Distance {
 public:
  explicit Distance(int metres) : metres_(metres) {}
  [[nodiscard]] int metres() const { return metres_; }

 private:
  int metres_;
};

class DelegatingValue {
 public:
  DelegatingValue() : DelegatingValue(7, "default") {}
  explicit DelegatingValue(int value) : DelegatingValue(value, "explicit") {}

  [[nodiscard]] int value() const { return value_; }
  [[nodiscard]] const std::string& source() const { return source_; }

 private:
  DelegatingValue(int value, std::string source)
      : value_(value), source_(std::move(source)) {}

  int value_;
  std::string source_;
};

class TrackedResource {
 public:
  TrackedResource(std::vector<std::string>& events, std::string payload)
      : events_(&events), payload_(std::move(payload)) {
    events_->push_back("construct");
  }

  TrackedResource(const TrackedResource& other)
      : events_(other.events_), payload_(other.payload_) {
    events_->push_back("copy");
  }

  TrackedResource(TrackedResource&& other) noexcept
      : events_(other.events_), payload_(std::move(other.payload_)) {
    events_->push_back("move");
  }

  TrackedResource& operator=(const TrackedResource&) = default;
  TrackedResource& operator=(TrackedResource&&) noexcept = default;

  [[nodiscard]] const std::string& payload() const { return payload_; }

 private:
  std::vector<std::string>* events_;
  std::string payload_;
};

struct OwnerWithDestructor {
  explicit OwnerWithDestructor(std::vector<std::string>& events)
      : resource(events, "owned") {}

  ~OwnerWithDestructor() {}

  TrackedResource resource;
};

struct RuleOfZeroOwner {
  RuleOfZeroOwner(std::vector<std::string>& events, std::string payload)
      : resource(events, std::move(payload)) {}

  TrackedResource resource;
};

class MoveOnlyOwner {
 public:
  explicit MoveOnlyOwner(int value) : value_(std::make_unique<int>(value)) {}

  MoveOnlyOwner(const MoveOnlyOwner&) = delete;
  MoveOnlyOwner& operator=(const MoveOnlyOwner&) = delete;
  MoveOnlyOwner(MoveOnlyOwner&&) noexcept = default;
  MoveOnlyOwner& operator=(MoveOnlyOwner&&) noexcept = default;

  [[nodiscard]] int value() const { return *value_; }

 private:
  std::unique_ptr<int> value_;
};

TEST(Construction, BasesAndMembersFollowDeclarationOrder) {
  std::vector<std::string> events;

  {
    EventOwner owner{events};
    EXPECT_EQ(
        events,
        (std::vector<std::string>{
            "construct base",
            "construct first member",
            "construct second member",
        }));
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "construct base",
          "construct first member",
          "construct second member",
          "destroy second member",
          "destroy first member",
          "destroy base",
      }));

  // 基类先于成员构造，成员按声明顺序而不是 mem-initializer-list 的书写顺序构造；
  // 析构严格反向。让一个成员初始化依赖声明在它后面的成员通常是隐藏 bug。
}

TEST(Construction, ExplicitPreventsAnAccidentalImplicitConversion) {
  static_assert(std::is_constructible_v<Distance, int>);
  static_assert(!std::is_convertible_v<int, Distance>);

  Distance distance{42};
  EXPECT_EQ(distance.metres(), 42);

  // explicit 允许直接初始化 Distance{42}，但禁止把 int 静默当成 Distance 传参或赋值。
  // 对单参数构造函数和转换运算符，应根据 API 是否真的表示隐式“同一种值”做选择。
}

TEST(Construction, DelegatingConstructorChoosesOneCanonicalInitializer) {
  DelegatingValue defaulted;
  DelegatingValue explicit_value{11};

  EXPECT_EQ(defaulted.value(), 7);
  EXPECT_EQ(defaulted.source(), "default");
  EXPECT_EQ(explicit_value.value(), 11);
  EXPECT_EQ(explicit_value.source(), "explicit");

  // 委托构造函数先完整执行目标构造函数，再执行自己的函数体。一个构造函数一旦委托，
  // 不能同时直接初始化其他成员；这能把不变量集中在一个规范化构造路径中。
}

TEST(SpecialMembers, CopyAndMoveConstructorsAreSelectedByValueCategory) {
  std::vector<std::string> events;
  TrackedResource source{events, "payload"};

  TrackedResource copied{source};
  TrackedResource moved{std::move(source)};

  EXPECT_EQ(copied.payload(), "payload");
  EXPECT_EQ(moved.payload(), "payload");
  EXPECT_EQ(events, (std::vector<std::string>{"construct", "copy", "move"}));

  // move 构造函数通常接管资源，但源对象仍必须保持可析构、可赋值的有效状态。
  // 只有具体类型另行承诺时，才能依赖 moved-from 对象的精确值。
}

TEST(SpecialMembers, UserDeclaredDestructorPreventsImplicitMoveGeneration) {
  std::vector<std::string> events;
  OwnerWithDestructor source{events};
  events.clear();

  OwnerWithDestructor destination{std::move(source)};
  EXPECT_EQ(destination.resource.payload(), "owned");
  EXPECT_EQ(events, (std::vector<std::string>{"copy"}));

  // 用户声明析构函数后，编译器不会隐式生成 move constructor。复制构造仍能绑定右值，
  // 所以 is_move_constructible 可能仍为 true；观察成员实际调用才能看出发生了复制。
}

TEST(SpecialMembers, RuleOfZeroLetsMembersPropagateCorrectMoveBehavior) {
  std::vector<std::string> events;
  RuleOfZeroOwner source{events, "payload"};
  events.clear();

  RuleOfZeroOwner destination{std::move(source)};
  EXPECT_EQ(destination.resource.payload(), "payload");
  EXPECT_EQ(events, (std::vector<std::string>{"move"}));

  // 不直接管理资源的类通常不应声明析构、复制或移动操作。让 string、vector、
  // unique_ptr 等成员组合所有权，编译器生成的特殊成员会自然获得正确语义。
}

TEST(SpecialMembers, DeletedCopyAndDefaultedMoveCreateAMoveOnlyType) {
  static_assert(!std::is_copy_constructible_v<MoveOnlyOwner>);
  static_assert(std::is_nothrow_move_constructible_v<MoveOnlyOwner>);

  MoveOnlyOwner source{13};
  MoveOnlyOwner destination{std::move(source)};
  EXPECT_EQ(destination.value(), 13);

  // = delete 让禁止的操作仍有清晰诊断并参与重载解析；= default 请求编译器逐成员
  // 生成操作。移动后不读取 source 的 unique_ptr，因为它的所有权已经转移。
}

}  // namespace
