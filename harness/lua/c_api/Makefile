# 该工程验证锁定头文件、静态库和动态模块的集成边界，不计入 Lua 课程文件数。
LUA_HOME ?= /opt/polyglot/lua-5.5.0
BUILD_DIR ?= /tmp/polyglot-lua-c-api
CC ?= cc

CPPFLAGS := -I$(LUA_HOME)/include
CFLAGS := -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
LUA_LIBS := -L$(LUA_HOME)/lib -llua -lm -ldl

.PHONY: all

all: $(BUILD_DIR)/polyglot_lua_host $(BUILD_DIR)/polyglot_native.so

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/polyglot_lua_host: polyglot_lua_host.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@ $(LUA_LIBS)

$(BUILD_DIR)/polyglot_native.so: polyglot_native.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared $< -o $@
