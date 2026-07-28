#include <lauxlib.h>
#include <lua.h>

static int native_add(lua_State *state) {
    lua_Integer left = luaL_checkinteger(state, 1);
    lua_Integer right = luaL_checkinteger(state, 2);
    lua_pushinteger(state, left + right);
    return 1;
}

static const luaL_Reg native_functions[] = {
    {"add", native_add},
    {NULL, NULL},
};

int luaopen_polyglot_native(lua_State *state) {
    luaL_newlib(state, native_functions);
    return 1;
}
