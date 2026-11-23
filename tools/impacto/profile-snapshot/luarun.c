/* Minimal Lua runner for profile-snapshot.py, built against the minilua of a patched impacto checkout (the Lua the
 * engine embeds): luarun <script.lua> [args...]; the arguments are in the global table `arg` (arg[1]...). */
#include <stdio.h>

#include "minilua/minilua.h"

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: luarun <script.lua> [args...]\n");
    return 2;
  }
  lua_State* L = luaL_newstate();
  luaL_openlibs(L);
  lua_createtable(L, argc, 0);
  for (int i = 1; i < argc; i++) {
    lua_pushstring(L, argv[i]);
    lua_rawseti(L, -2, i - 1);
  }
  lua_setglobal(L, "arg");
  if (luaL_dofile(L, argv[1]) != LUA_OK) {
    fprintf(stderr, "%s\n", lua_tostring(L, -1));
    lua_close(L);
    return 1;
  }
  lua_close(L);
  return 0;
}
