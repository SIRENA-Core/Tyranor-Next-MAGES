# mo6tw-pc 数据生成脚本

用来生成补丁系列里 `profiles/mo6tw-pc*` 那部分数据的脚本。**只有代码，不含任何游戏内容**：它们读的是你自己的上游 Impacto 检出（`profiles/mo6tw` 的 PS3 配置），
或你从自己的游戏拷贝里解出来的图集；结果写进检出的 `profiles/mo6tw-pc/`，再按 [补丁流程](../../../engine/impacto/patches/README.md) 提交并导出。

所有路径都从命令行传入，脚本里没有写死的目录。

| 脚本 | 作用 | 依赖 |
| --- | --- | --- |
| `gen_hud.py <检出>` | 把 `profiles/mo6tw` 的 HUD／对话框配置按 1280x720 → 1920x1080 放大 1.5 倍，生成 `profiles/mo6tw-pc/dialogue.lua` 与 `hud/*.lua`。PC 版 `system.cpk` 的 data01 恰好是 PS3 Data 图集的 1.5 倍，只用到它的文件是精确的；标题、存档、选项、附加内容等菜单的图集在 PC 上重排过，坐标只是近似，生成文件带 `TODO(tyn)` 头 | 标准库 |
| `gen_hud_common.py` | `gen_hud.py` 的缩放辅助（哪些键是几何量、怎样取整），不单独运行 | 标准库 |
| `gen_widths.py <检出> <font.png> <font_ht.png> <font_kt.png>` | PC 版没有字宽表，按三张字体图集（`system.cpk` 的 font／font_ht／font_kt，id 10／11／12）逐格量墨迹，生成 `profiles/mo6tw-pc/font-widths.lua`；三张图集结果不一致就报错 | Pillow（`pip install pillow`） |
| `seg.py <图集.png>` | 打印图集里不透明像素的横向分段与纵向条带，手工标定菜单坐标时读精灵边界用 | Pillow |
| `lua_balance.py <文件.lua>...` | 没有 Lua 解释器时的括号与 `end` 配对检查 | 标准库 |

```sh
python tools/impacto/mo6tw-pc/gen_hud.py ~/impacto-patches
python tools/impacto/mo6tw-pc/gen_widths.py ~/impacto-patches font.png font_ht.png font_kt.png
python tools/impacto/mo6tw-pc/lua_balance.py ~/impacto-patches/profiles/mo6tw-pc/dialogue.lua
```

字体图集要自己从游戏里解出来，不要提交到本仓库。生成结果（Lua 数据）属于补丁系列，随补丁一起公开；游戏的图集与脚本不属于。
