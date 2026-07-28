#include <stdio.h>

#include <lauxlib.h>
#include <lua.h>

typedef struct {
    lua_Integer value;
    int closed;
} native_box;

static int finalized_boxes = 0;

static native_box *check_box(lua_State *state, int index) {
    return luaL_checkudata(state, index, "polyglot.native_box");
}

static int native_add(lua_State *state) {
    lua_Integer left = luaL_checkinteger(state, 1);
    lua_Integer right = luaL_checkinteger(state, 2);
    lua_pushinteger(state, left + right);
    return 1;
}

static int native_fail(lua_State *state) {
    return luaL_error(state, "native failure: %s", luaL_optstring(state, 1, "unknown"));
}

static int native_record(lua_State *state) {
    const char *label = luaL_checkstring(state, 1);
    lua_Integer value = luaL_checkinteger(state, 2);
    lua_createtable(state, 0, 2);
    lua_pushstring(state, label);
    lua_setfield(state, -2, "label");
    lua_pushinteger(state, value);
    lua_setfield(state, -2, "value");
    return 1;
}

static int counter_call(lua_State *state) {
    lua_Integer current = lua_tointeger(state, lua_upvalueindex(1));
    lua_Integer step = luaL_optinteger(state, 1, 1);
    current += step;
    lua_pushinteger(state, current);
    lua_replace(state, lua_upvalueindex(1));
    lua_pushinteger(state, current);
    return 1;
}

static int native_counter(lua_State *state) {
    lua_Integer start = luaL_optinteger(state, 1, 0);
    lua_pushinteger(state, start);
    lua_pushcclosure(state, counter_call, 1);
    return 1;
}

static int box_get(lua_State *state) {
    native_box *box = check_box(state, 1);
    luaL_argcheck(state, !box->closed, 1, "box is closed");
    lua_pushinteger(state, box->value);
    return 1;
}

static int box_set(lua_State *state) {
    native_box *box = check_box(state, 1);
    luaL_argcheck(state, !box->closed, 1, "box is closed");
    box->value = luaL_checkinteger(state, 2);
    lua_settop(state, 1);
    return 1;
}

static int box_label(lua_State *state) {
    check_box(state, 1);
    lua_getiuservalue(state, 1, 1);
    return 1;
}

static int close_box(native_box *box) {
    if (!box->closed) {
        box->closed = 1;
        finalized_boxes += 1;
    }
    return 0;
}

static int box_close(lua_State *state) {
    return close_box(check_box(state, 1));
}

static int box_gc(lua_State *state) {
    return close_box(check_box(state, 1));
}

static int box_tostring(lua_State *state) {
    native_box *box = check_box(state, 1);
    lua_pushfstring(
        state,
        "native_box(%I,%s)",
        box->value,
        box->closed ? "closed" : "open"
    );
    return 1;
}

static int native_new_box(lua_State *state) {
    lua_Integer value = luaL_checkinteger(state, 1);
    native_box *box = lua_newuserdatauv(state, sizeof(*box), 2);
    box->value = value;
    box->closed = 0;
    lua_pushvalue(state, 2);
    lua_setiuservalue(state, -2, 1);
    lua_createtable(state, 0, 1);
    lua_pushboolean(state, 1);
    lua_setfield(state, -2, "owned");
    lua_setiuservalue(state, -2, 2);
    luaL_setmetatable(state, "polyglot.native_box");
    return 1;
}

static int native_finalized_boxes(lua_State *state) {
    lua_pushinteger(state, finalized_boxes);
    return 1;
}

static const luaL_Reg box_methods[] = {
    {"get", box_get},
    {"set", box_set},
    {"label", box_label},
    {"close", box_close},
    {NULL, NULL},
};

static const luaL_Reg box_metamethods[] = {
    {"__close", box_close},
    {"__gc", box_gc},
    {"__tostring", box_tostring},
    {NULL, NULL},
};

static const luaL_Reg native_functions[] = {
    {"add", native_add},
    {"counter", native_counter},
    {"fail", native_fail},
    {"finalized_boxes", native_finalized_boxes},
    {"new_box", native_new_box},
    {"record", native_record},
    {NULL, NULL},
};

int luaopen_polyglot_native(lua_State *state) {
    if (luaL_newmetatable(state, "polyglot.native_box")) {
        luaL_setfuncs(state, box_metamethods, 0);
        lua_createtable(state, 0, 4);
        luaL_setfuncs(state, box_methods, 0);
        lua_setfield(state, -2, "__index");
        lua_pushliteral(state, "polyglot.native_box");
        lua_setfield(state, -2, "__name");
    }
    lua_pop(state, 1);
    luaL_newlib(state, native_functions);
    lua_pushliteral(state, LUA_RELEASE);
    lua_setfield(state, -2, "release");
    return 1;
}
