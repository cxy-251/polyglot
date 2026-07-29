/* 可执行的 Lua C API fixture；Lua 课程通过小型主题测试解释这里的公开契约。 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

#define CASE_CHECK(condition)                                                       \
    do {                                                                            \
        if (!(condition)) {                                                         \
            fprintf(stderr, "%s:%d: check failed: %s\n", __func__, __LINE__, #condition); \
            return 0;                                                               \
        }                                                                           \
    } while (0)

typedef int (*case_function)(lua_State *state);

typedef struct {
    char *data;
    size_t size;
    int calls;
    int saw_final_call;
} dump_buffer;

typedef struct {
    size_t allocations;
    size_t releases;
} allocator_stats;

typedef struct {
    char text[128];
    size_t length;
    int pieces;
} warning_log;

static int userdata_finalized = 0;
static int hook_calls = 0;

static int run_chunk(lua_State *state, const char *source, int results) {
    if (luaL_loadstring(state, source) != LUA_OK) {
        return 0;
    }
    return lua_pcall(state, 0, results, 0) == LUA_OK;
}

static int host_add(lua_State *state) {
    lua_Integer left = luaL_checkinteger(state, 1);
    lua_Integer right = luaL_checkinteger(state, 2);
    lua_pushinteger(state, left + right);
    return 1;
}

static int closure_add(lua_State *state) {
    lua_Integer base = lua_tointeger(state, lua_upvalueindex(1));
    lua_Integer increment = luaL_checkinteger(state, 1);
    lua_pushinteger(state, base + increment);
    return 1;
}

static int protected_failure(lua_State *state) {
    lua_pushliteral(state, "protected failure");
    return lua_error(state);
}

static int panic_handler(lua_State *state) {
    (void)state;
    return 0;
}

static int continuation(lua_State *state, int status, lua_KContext context) {
    lua_Integer resumed;
    if (status != LUA_YIELD) {
        return luaL_error(state, "unexpected continuation status");
    }
    resumed = luaL_checkinteger(state, 1);
    lua_pushinteger(state, (lua_Integer)context + resumed);
    return 1;
}

static int yielding_function(lua_State *state) {
    lua_pushliteral(state, "yielded");
    return lua_yieldk(state, 1, 40, continuation);
}

static int userdata_gc(lua_State *state) {
    int *value = lua_touserdata(state, 1);
    if (value != NULL && *value == 42) {
        userdata_finalized += 1;
    }
    return 0;
}

static void *tracking_allocator(void *opaque, void *pointer, size_t old_size, size_t new_size) {
    allocator_stats *stats = opaque;
    (void)old_size;
    if (new_size == 0) {
        free(pointer);
        stats->releases += 1;
        return NULL;
    }
    if (pointer == NULL) {
        stats->allocations += 1;
    }
    return realloc(pointer, new_size);
}

static void warning_handler(void *opaque, const char *message, int to_continue) {
    warning_log *log = opaque;
    size_t available = sizeof(log->text) - log->length - 1;
    size_t size = strlen(message);
    if (size > available) {
        size = available;
    }
    memcpy(log->text + log->length, message, size);
    log->length += size;
    log->text[log->length] = '\0';
    log->pieces += 1;
    (void)to_continue;
}

static void count_hook(lua_State *state, lua_Debug *activation_record) {
    (void)state;
    if (activation_record->event == LUA_HOOKCOUNT) {
        hook_calls += 1;
    }
}

static int dump_writer(lua_State *state, const void *data, size_t size, void *opaque) {
    dump_buffer *buffer = opaque;
    char *expanded;
    (void)state;
    buffer->calls += 1;
    if (data == NULL && size == 0) {
        buffer->saw_final_call = 1;
        return 0;
    }
    expanded = realloc(buffer->data, buffer->size + size);
    if (expanded == NULL) {
        return 1;
    }
    buffer->data = expanded;
    memcpy(buffer->data + buffer->size, data, size);
    buffer->size += size;
    return 0;
}

static const char *dump_reader(lua_State *state, void *opaque, size_t *size) {
    dump_buffer *buffer = opaque;
    (void)state;
    if (buffer->data == NULL) {
        *size = 0;
        return NULL;
    }
    *size = buffer->size;
    {
        const char *result = buffer->data;
        buffer->data = NULL;
        return result;
    }
}

static int auxiliary_module(lua_State *state) {
    static const luaL_Reg functions[] = {
        {"add", host_add},
        {NULL, NULL},
    };
    luaL_newlib(state, functions);
    return 1;
}

static void *external_string_free(
    void *opaque,
    void *pointer,
    size_t old_size,
    size_t new_size
) {
    int *release_count = opaque;
    (void)old_size;
    if (new_size == 0) {
        *release_count += 1;
        free(pointer);
        return NULL;
    }
    return realloc(pointer, new_size);
}

static int case_state(lua_State *state) {
    CASE_CHECK(lua_version(state) == LUA_VERSION_NUM);
    CASE_CHECK(run_chunk(state, "return 6 * 7", 1));
    CASE_CHECK(lua_isinteger(state, -1));
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    return 1;
}

static int case_selected_libraries(lua_State *state) {
    lua_State *limited = luaL_newstate();
    (void)state;
    CASE_CHECK(limited != NULL);
    luaL_openselectedlibs(limited, LUA_GLIBK | LUA_MATHLIBK, 0);
    CASE_CHECK(lua_getglobal(limited, "math") == LUA_TTABLE);
    lua_pop(limited, 1);
    CASE_CHECK(lua_getglobal(limited, "io") == LUA_TNIL);
    lua_pop(limited, 1);
    CASE_CHECK(run_chunk(limited, "return type(print), math.sqrt(81), io", 3));
    CASE_CHECK(strcmp(lua_tostring(limited, -3), "function") == 0);
    CASE_CHECK(lua_tonumber(limited, -2) == 9.0);
    CASE_CHECK(lua_isnil(limited, -1));
    lua_close(limited);
    return 1;
}

static int case_stack(lua_State *state) {
    int marker = 42;
    int absolute;
    const char *pointer;
    lua_settop(state, 0);
    lua_pushinteger(state, 42);
    lua_pushnumber(state, 3.5);
    lua_pushlstring(state, "a\0b", 3);
    lua_pushboolean(state, 1);
    lua_pushnil(state);
    lua_pushlightuserdata(state, &marker);
    CASE_CHECK(lua_gettop(state) == 6);
    absolute = lua_absindex(state, -4);
    CASE_CHECK(absolute == 3);
    CASE_CHECK(lua_type(state, 1000) == LUA_TNONE);
    CASE_CHECK(lua_isnone(state, 1000));
    CASE_CHECK(lua_touserdata(state, -1) == &marker);
    pointer = lua_tolstring(state, absolute, NULL);
    CASE_CHECK(pointer != NULL && memcmp(pointer, "a\0b", 3) == 0);
    CASE_CHECK(lua_checkstack(state, 100));
    lua_pushvalue(state, absolute);
    lua_gc(state, LUA_GCCOLLECT);
    CASE_CHECK(memcmp(pointer, "a\0b", 3) == 0);
    lua_settop(state, 0);
    return 1;
}

static int case_tables_registry(lua_State *state) {
    static const char registry_key = '\0';
    int reference;
    lua_createtable(state, 2, 2);
    lua_pushinteger(state, 42);
    lua_setfield(state, -2, "answer");
    lua_pushliteral(state, "first");
    lua_seti(state, -2, 1);
    lua_pushliteral(state, "private");
    lua_rawsetp(state, -2, &registry_key);
    CASE_CHECK(lua_getfield(state, -1, "answer") == LUA_TNUMBER);
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    CASE_CHECK(lua_geti(state, -1, 1) == LUA_TSTRING);
    CASE_CHECK(strcmp(lua_tostring(state, -1), "first") == 0);
    lua_pop(state, 1);
    CASE_CHECK(lua_rawgetp(state, -1, &registry_key) == LUA_TSTRING);
    lua_pop(state, 1);
    reference = luaL_ref(state, LUA_REGISTRYINDEX);
    CASE_CHECK(reference >= 0);
    CASE_CHECK(lua_rawgeti(state, LUA_REGISTRYINDEX, reference) == LUA_TTABLE);
    lua_pop(state, 1);
    luaL_unref(state, LUA_REGISTRYINDEX, reference);
    return 1;
}

static int case_closures(lua_State *state) {
    lua_pushinteger(state, 40);
    lua_pushcclosure(state, closure_add, 1);
    lua_setglobal(state, "host_add");
    CASE_CHECK(run_chunk(state, "return host_add(2)", 1));
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    lua_getglobal(state, "host_add");
    lua_pushinteger(state, 2);
    lua_call(state, 1, 1);
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    return 1;
}

static int case_protected(lua_State *state) {
    lua_CFunction old_panic;
    int status;
    lua_pushcfunction(state, protected_failure);
    status = lua_pcall(state, 0, 0, 0);
    CASE_CHECK(status == LUA_ERRRUN);
    CASE_CHECK(strstr(lua_tostring(state, -1), "protected failure") != NULL);
    lua_pop(state, 1);
    status = luaL_loadstring(state, "local =");
    CASE_CHECK(status == LUA_ERRSYNTAX);
    CASE_CHECK(lua_status(state) == LUA_OK);
    lua_pop(state, 1);
    old_panic = lua_atpanic(state, panic_handler);
    CASE_CHECK(lua_atpanic(state, old_panic) == panic_handler);
    return 1;
}

static int case_continuation(lua_State *state) {
    lua_State *thread = lua_newthread(state);
    int results = 0;
    int status;
    lua_pushcfunction(thread, yielding_function);
    status = lua_resume(thread, state, 0, &results);
    CASE_CHECK(status == LUA_YIELD);
    CASE_CHECK(results == 1);
    CASE_CHECK(strcmp(lua_tostring(thread, -1), "yielded") == 0);
    lua_settop(thread, 0);
    lua_pushinteger(thread, 2);
    status = lua_resume(thread, state, 1, &results);
    CASE_CHECK(status == LUA_OK);
    CASE_CHECK(results == 1);
    CASE_CHECK(lua_tointeger(thread, -1) == 42);
    CASE_CHECK(lua_closethread(thread, state) == LUA_OK);
    lua_pop(state, 1);
    return 1;
}

static int case_userdata(lua_State *state) {
    int *payload;
    userdata_finalized = 0;
    payload = lua_newuserdatauv(state, sizeof(*payload), 2);
    *payload = 42;
    lua_pushliteral(state, "label");
    CASE_CHECK(lua_setiuservalue(state, -2, 1));
    lua_createtable(state, 0, 1);
    lua_pushboolean(state, 1);
    lua_setfield(state, -2, "owned");
    CASE_CHECK(lua_setiuservalue(state, -2, 2));
    lua_createtable(state, 0, 1);
    lua_pushcfunction(state, userdata_gc);
    lua_setfield(state, -2, "__gc");
    CASE_CHECK(lua_setmetatable(state, -2));
    CASE_CHECK(lua_getiuservalue(state, -1, 1) == LUA_TSTRING);
    CASE_CHECK(strcmp(lua_tostring(state, -1), "label") == 0);
    lua_pop(state, 1);
    CASE_CHECK(lua_getiuservalue(state, -1, 2) == LUA_TTABLE);
    lua_getfield(state, -1, "owned");
    CASE_CHECK(lua_toboolean(state, -1));
    lua_pop(state, 3);
    lua_gc(state, LUA_GCCOLLECT);
    CASE_CHECK(userdata_finalized == 1);
    return 1;
}

static int case_allocator_warning(lua_State *state) {
    allocator_stats stats = {0, 0};
    warning_log log = {{0}, 0, 0};
    lua_State *tracked = lua_newstate(tracking_allocator, &stats, 12345U);
    (void)state;
    CASE_CHECK(tracked != NULL);
    luaL_openlibs(tracked);
    CASE_CHECK(run_chunk(tracked, "return string.rep('x', 1000)", 1));
    lua_setwarnf(tracked, warning_handler, &log);
    lua_warning(tracked, "first ", 1);
    lua_warning(tracked, "second", 0);
    CASE_CHECK(strcmp(log.text, "first second") == 0);
    CASE_CHECK(log.pieces == 2);
    lua_close(tracked);
    CASE_CHECK(stats.allocations > 0);
    CASE_CHECK(stats.releases > 0);
    return 1;
}

static int case_hook(lua_State *state) {
    hook_calls = 0;
    lua_sethook(state, count_hook, LUA_MASKCOUNT, 10);
    CASE_CHECK(run_chunk(state, "local n=0; for i=1,100 do n=n+i end; return n", 1));
    lua_sethook(state, NULL, 0, 0);
    CASE_CHECK(lua_tointeger(state, -1) == 5050);
    CASE_CHECK(hook_calls > 0);
    CASE_CHECK(lua_gethook(state) == NULL);
    lua_pop(state, 1);
    return 1;
}

static int case_dump_load(lua_State *state) {
    dump_buffer buffer = {NULL, 0, 0, 0};
    dump_buffer reader;
    int top;
    CASE_CHECK(luaL_loadstring(state, "return 6 * 7") == LUA_OK);
    top = lua_gettop(state);
    CASE_CHECK(lua_dump(state, dump_writer, &buffer, 1) == 0);
    CASE_CHECK(lua_gettop(state) == top);
    CASE_CHECK(buffer.size > 4);
    CASE_CHECK(memcmp(buffer.data, "\x1bLua", 4) == 0);
    CASE_CHECK(buffer.calls > 1);
    CASE_CHECK(buffer.saw_final_call);
    lua_pop(state, 1);
    reader = buffer;
    CASE_CHECK(lua_load(state, dump_reader, &reader, "dumped", "b") == LUA_OK);
    CASE_CHECK(lua_pcall(state, 0, 1, 0) == LUA_OK);
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    free(buffer.data);
    return 1;
}

static int case_state_isolation(lua_State *state) {
    lua_State *first = luaL_newstate();
    lua_State *second = luaL_newstate();
    (void)state;
    CASE_CHECK(first != NULL && second != NULL);
    lua_pushinteger(first, 10);
    lua_setglobal(first, "value");
    lua_pushinteger(second, 20);
    lua_setglobal(second, "value");
    CASE_CHECK(lua_getglobal(first, "value") == LUA_TNUMBER);
    CASE_CHECK(lua_tointeger(first, -1) == 10);
    CASE_CHECK(lua_getglobal(second, "value") == LUA_TNUMBER);
    CASE_CHECK(lua_tointeger(second, -1) == 20);
    lua_pushlightuserdata(first, first);
    lua_rawsetp(first, LUA_REGISTRYINDEX, first);
    CASE_CHECK(lua_rawgetp(second, LUA_REGISTRYINDEX, first) == LUA_TNIL);
    lua_close(first);
    lua_close(second);
    return 1;
}

static int case_structured(lua_State *state) {
    lua_pushcfunction(state, host_add);
    lua_setglobal(state, "host_add");
    CASE_CHECK(run_chunk(
        state,
        "local input={left=19,right=23}; "
        "return {answer=host_add(input.left,input.right),kind='result'}",
        1
    ));
    CASE_CHECK(lua_istable(state, -1));
    lua_getfield(state, -1, "answer");
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 1);
    lua_getfield(state, -1, "kind");
    CASE_CHECK(strcmp(lua_tostring(state, -1), "result") == 0);
    lua_pop(state, 2);
    return 1;
}

static int case_auxiliary(lua_State *state) {
    const char *replaced;
    int reference;
    luaL_checkversion(state);
    replaced = luaL_gsub(state, "a-b-c", "-", ":");
    CASE_CHECK(strcmp(replaced, "a:b:c") == 0);
    lua_pop(state, 1);
    luaL_requiref(state, "polyglot_aux", auxiliary_module, 0);
    CASE_CHECK(lua_istable(state, -1));
    reference = luaL_ref(state, LUA_REGISTRYINDEX);
    CASE_CHECK(lua_rawgeti(state, LUA_REGISTRYINDEX, reference) == LUA_TTABLE);
    lua_getfield(state, -1, "add");
    lua_pushinteger(state, 20);
    lua_pushinteger(state, 22);
    lua_call(state, 2, 1);
    CASE_CHECK(lua_tointeger(state, -1) == 42);
    lua_pop(state, 2);
    luaL_unref(state, LUA_REGISTRYINDEX, reference);
    return 1;
}

static int case_external_string(lua_State *state) {
    int releases = 0;
    const size_t size = 64;
    char *buffer = malloc(size + 1);
    const char *pushed;
    CASE_CHECK(buffer != NULL);
    memset(buffer, 'x', size);
    buffer[size] = '\0';
    pushed = lua_pushexternalstring(
        state,
        buffer,
        size,
        external_string_free,
        &releases
    );
    CASE_CHECK(pushed == buffer);
    CASE_CHECK(lua_rawlen(state, -1) == size);
    CASE_CHECK(lua_tolstring(state, -1, NULL) == buffer);
    lua_pop(state, 1);
    lua_gc(state, LUA_GCCOLLECT);
    CASE_CHECK(releases == 1);
    return 1;
}

static int case_version_gc(lua_State *state) {
    int pause;
    CASE_CHECK(LUA_VERSION_NUM == 505);
    CASE_CHECK(LUA_VERSION_RELEASE_NUM == 50500);
    CASE_CHECK(strcmp(LUA_RELEASE, "Lua 5.5.0") == 0);
    CASE_CHECK(lua_version(state) == 505);
    pause = lua_gc(state, LUA_GCPARAM, LUA_GCPPAUSE, -1);
    CASE_CHECK(pause >= 0);
    CASE_CHECK(lua_gc(state, LUA_GCPARAM, LUA_GCPPAUSE, pause) == pause);
    CASE_CHECK(lua_gc(state, LUA_GCGEN) == LUA_GCINC);
    CASE_CHECK(lua_gc(state, LUA_GCINC) == LUA_GCGEN);
    return 1;
}

typedef struct {
    const char *name;
    case_function function;
} case_entry;

static const case_entry cases[] = {
    {"state", case_state},
    {"selected-libraries", case_selected_libraries},
    {"stack", case_stack},
    {"tables-registry", case_tables_registry},
    {"closures", case_closures},
    {"protected", case_protected},
    {"continuation", case_continuation},
    {"userdata", case_userdata},
    {"allocator-warning", case_allocator_warning},
    {"hook", case_hook},
    {"dump-load", case_dump_load},
    {"state-isolation", case_state_isolation},
    {"structured", case_structured},
    {"auxiliary", case_auxiliary},
    {"external-string", case_external_string},
    {"version-gc", case_version_gc},
    {NULL, NULL},
};

int main(int argc, char **argv) {
    lua_State *state;
    const case_entry *entry;

    if (argc != 2) {
        fprintf(stderr, "usage: polyglot_lua_host CASE\n");
        return 2;
    }
    state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "luaL_newstate failed\n");
        return 1;
    }
    luaL_openlibs(state);

    for (entry = cases; entry->name != NULL; entry += 1) {
        if (strcmp(entry->name, argv[1]) == 0) {
            int passed = entry->function(state);
            lua_close(state);
            if (!passed) {
                fprintf(stderr, "C API case failed: %s\n", entry->name);
                return 1;
            }
            printf("C API case passed: %s\n", entry->name);
            return 0;
        }
    }

    lua_close(state);
    fprintf(stderr, "unknown C API case: %s\n", argv[1]);
    return 2;
}
