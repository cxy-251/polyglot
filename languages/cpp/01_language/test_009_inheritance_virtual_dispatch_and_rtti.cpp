// polyglot-covers:
// - cpp.language.public-private-and-virtual-inheritance
// - cpp.language.virtual-dispatch-override-and-final
// - cpp.language.abstract-classes-and-pure-virtual-functions
// - cpp.language.virtual-destructors
// - cpp.language.construction-destruction-dispatch
// - cpp.language.object-slicing
// - cpp.language.dynamic-cast-and-typeid

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <type_traits>
#include <typeinfo>
#include <utility>
#include <vector>

namespace {

class Animal {
 public:
  explicit Animal(std::string name) : name_(std::move(name)) {}
  virtual ~Animal() = default;

  virtual std::string sound() const { return "unknown"; }
  std::string name() const { return name_; }

 private:
  std::string name_;
};

class Dog final : public Animal {
 public:
  explicit Dog(std::string name) : Animal(std::move(name)) {}
  std::string sound() const override { return "woof"; }
};

class AbstractShape {
 public:
  virtual ~AbstractShape() = default;
  virtual double area() const = 0;
};

class Square : public AbstractShape {
 public:
  explicit Square(double side) : side_(side) {}
  double area() const override { return side_ * side_; }

 private:
  double side_;
};

class DestructionBase {
 public:
  explicit DestructionBase(std::vector<std::string>& events) : events_(events) {}
  virtual ~DestructionBase() { events_.push_back("base destructor"); }

 protected:
  std::vector<std::string>& events_;
};

class DestructionDerived : public DestructionBase {
 public:
  explicit DestructionDerived(std::vector<std::string>& events)
      : DestructionBase(events) {}

  ~DestructionDerived() override { events_.push_back("derived destructor"); }
};

class DispatchBase {
 public:
  explicit DispatchBase(std::vector<std::string>& events) : events_(events) {
    events_.push_back("base constructor sees " + phase());
  }

  virtual ~DispatchBase() { events_.push_back("base destructor sees " + phase()); }

  virtual std::string phase() const { return "base"; }

 protected:
  std::vector<std::string>& events_;
};

class DispatchDerived : public DispatchBase {
 public:
  explicit DispatchDerived(std::vector<std::string>& events) : DispatchBase(events) {
    events_.push_back("derived constructor sees " + phase());
  }

  ~DispatchDerived() override {
    events_.push_back("derived destructor sees " + phase());
  }

  std::string phase() const override { return "derived"; }
};

class PublicDerived : public Animal {
 public:
  PublicDerived() : Animal("public") {}
};

class PrivateDerived : private Animal {
 public:
  PrivateDerived() : Animal("private") {}
};

struct VirtualRoot {
  int value{0};
};

struct LeftBranch : virtual VirtualRoot {};
struct RightBranch : virtual VirtualRoot {};
struct Diamond : LeftBranch, RightBranch {};

Animal slice_to_animal(const Animal& animal) { return animal; }

TEST(Inheritance, PublicInheritanceProvidesAnImplicitBaseConversion) {
  static_assert(std::is_convertible_v<PublicDerived*, Animal*>);
  static_assert(!std::is_convertible_v<PrivateDerived*, Animal*>);

  PublicDerived derived;
  Animal& base = derived;
  EXPECT_EQ(base.name(), "public");

  // public inheritance 表达可替代的 is-a 关系，并允许调用者进行派生到基类转换。
  // private inheritance 只把基类当实现细节，转换在类外不可访问，不等同于组合接口。
}

TEST(VirtualFunctions, CallsThroughBaseReferencesUseTheFinalOverrider) {
  Dog dog{"Milo"};
  Animal& animal = dog;

  EXPECT_EQ(animal.sound(), "woof");
  EXPECT_EQ(animal.Animal::sound(), "unknown");
  EXPECT_EQ(animal.name(), "Milo");

  // virtual 调用根据对象动态类型选择 final overrider；限定调用 Animal::sound() 会
  // 明确绕过虚分派。非 virtual 的 name() 始终按表达式静态类型解析。
}

TEST(VirtualFunctions, PureVirtualFunctionMakesTheBaseAbstract) {
  static_assert(std::is_abstract_v<AbstractShape>);
  static_assert(!std::is_abstract_v<Square>);

  Square square{3.0};
  AbstractShape& shape = square;
  EXPECT_DOUBLE_EQ(shape.area(), 9.0);

  // 纯虚函数定义接口槽位，并不要求基类完全没有实现；但只要仍有未覆盖的纯虚函数，
  // 类型就是 abstract，不能直接构造对象。抽象多态基类通常仍需要虚析构函数。
}

TEST(VirtualFunctions, VirtualDestructorDeletesTheWholeDerivedObject) {
  std::vector<std::string> events;

  {
    std::unique_ptr<DestructionBase> object =
        std::make_unique<DestructionDerived>(events);
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{"derived destructor", "base destructor"}));

  // 通过基类指针拥有派生对象时，基类析构必须是 virtual；否则 delete 的行为未定义。
  // 如果基类从不负责多态删除，可以用 protected 非虚析构等方式明确禁止这种所有权。
}

TEST(VirtualFunctions, ConstructionAndDestructionRestrictDynamicDispatch) {
  std::vector<std::string> events;

  {
    DispatchDerived object{events};
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "base constructor sees base",
          "derived constructor sees derived",
          "derived destructor sees derived",
          "base destructor sees base",
      }));

  // 构造基类子对象时派生部分尚未开始，析构基类时派生部分已经结束，所以虚调用只到
  // 当前正在构造或析构的类。不要依赖构造函数调用派生覆盖来建立不变量。
}

TEST(Inheritance, CopyingIntoABaseObjectSlicesTheDerivedPart) {
  Dog dog{"Rex"};
  Animal sliced = slice_to_animal(dog);

  EXPECT_EQ(sliced.name(), "Rex");
  EXPECT_EQ(sliced.sound(), "unknown");

  // 按值接收或返回基类会创建独立基类对象，派生子对象被切掉，动态类型也变成基类。
  // 多态接口应使用引用、指针或明确的多态值包装，而不是按值传递基类。
}

TEST(Rtti, DynamicCastChecksTheRuntimeTypeOfAPolymorphicObject) {
  Dog dog{"Spot"};
  Animal& animal = dog;

  Dog* dog_pointer = dynamic_cast<Dog*>(&animal);
  ASSERT_NE(dog_pointer, nullptr);
  EXPECT_EQ(dog_pointer->sound(), "woof");

  PublicDerived other;
  Animal* other_base = &other;
  EXPECT_EQ(dynamic_cast<Dog*>(other_base), nullptr);
  EXPECT_THROW((void)dynamic_cast<Dog&>(*other_base), std::bad_cast);

  EXPECT_EQ(typeid(animal), typeid(Dog));
  EXPECT_EQ(typeid(other), typeid(PublicDerived));

  // 对指针失败时 dynamic_cast 返回 nullptr，对引用失败时抛 bad_cast。typeid 通过
  // 多态 glvalue 观察动态类型；对非多态表达式通常只报告静态类型。
}

TEST(Inheritance, VirtualBaseProducesOneSharedRootSubobject) {
  Diamond diamond;
  diamond.LeftBranch::value = 41;
  diamond.RightBranch::value += 1;

  VirtualRoot* through_left = static_cast<LeftBranch*>(&diamond);
  VirtualRoot* through_right = static_cast<RightBranch*>(&diamond);

  EXPECT_EQ(through_left, through_right);
  EXPECT_EQ(diamond.value, 42);

  // virtual inheritance 让菱形路径共享同一个虚基类子对象。最派生类负责初始化虚基类，
  // 中间基类给出的虚基初始化只在它本身是最派生对象时生效。
}

}  // namespace
