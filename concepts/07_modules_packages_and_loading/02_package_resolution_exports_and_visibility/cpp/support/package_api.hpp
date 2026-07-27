#pragma once

namespace package_api {

inline int public_value() {
  return 1;
}

namespace detail {

inline int helper() {
  return 2;
}

}  // namespace detail

class Service {
 public:
  int read() const {
    return state_;
  }

 private:
  int state_{3};
};

}  // namespace package_api
