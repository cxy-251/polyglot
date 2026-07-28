#include <stdio.h>
#include <string.h>

#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

static int fail(lua_State *state, const char *message) {
    if (state != NULL) {
        lua_close(state);
    }
    fprintf(stderr, "%s\n", message);
    return 1;
}

static int run_state_case(lua_State *state) {
    luaL_openlibs(state);
    if (luaL_loadstring(state, "return 6 * 7") != LUA_OK) {
        return 0;
    }
    if (lua_pcall(state, 0, 1, 0) != LUA_OK) {
        return 0;
    }
    return lua_isinteger(state, -1) && lua_tointeger(state, -1) == 42;
}

int main(int argc, char **argv) {
    lua_State *state;

    if (argc != 2 || strcmp(argv[1], "state") != 0) {
        fprintf(stderr, "usage: polyglot_lua_host state\n");
        return 2;
    }

    state = luaL_newstate();
    if (state == NULL) {
        return fail(NULL, "luaL_newstate failed");
    }
    if (!run_state_case(state)) {
        return fail(state, "state case failed");
    }

    lua_close(state);
    puts("C API case passed: state");
    return 0;
}
