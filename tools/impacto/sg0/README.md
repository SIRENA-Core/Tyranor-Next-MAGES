# STEINS;GATE 0 手机（RINE）的翻译工具

S;G0 的手机（主屏、RINE、Amadeus、设定、壁纸、铃声）有 90 多个函数，逐个手写移植太慢，也容易出错。这里的做法是：用 Ghidra 把原版 `Game.exe` 反编译，再由 `translate_phone.py` 把手机模块（0x46b600..0x478000）机械地翻译成引擎能编译的 C++。

原版全局变量保留原地址，放在“模拟内存”（`Sg0Emu::At(地址)`）里，所以反编译出来的交错表达式（如 `(&DAT_0197afe4)[i * 5]`）意思不变。原版调用的外部函数保留 `FUN_00xxxxxx` 名字，在引擎里用 `phoneshim.cpp` 实现：绘图、文字排版、点击区域、旗标、输入。RINE 对话读取器直接读剧本字节，在 `phonerine.cpp` 里手写移植。

## 重新生成

1. 用 Ghidra 导入并分析 `Game.exe`（Steam 版）。
2. 导出所有函数的反编译结果：`analyzeHeadless ... -postScript DumpRange.java 00401000 00549000 all.c`
3. 导出全局变量类型：`analyzeHeadless ... -postScript DumpData.java data.txt 01970000 01990000 00540000 005d0000 00dc0000 00e50000 02ed0000 02ef0000 032f0000 03300000`
4. 运行：

   ```
   python translate_phone.py all.c data.txt Game.exe <补丁树>/src/games/sg0/phonecode.cpp $(cat phone_skip.txt)
   ```

   它会写出 `phonecode.cpp` 和同目录的 `phoneglobals.h`。

生成文件不要手改。反编译里需要修正的地方（比如 Ghidra 把同一个变量拆开、指针被当成 32 位整数）记录在 `phone_fixes.py` 里，按精确文本替换；找不到要替换的文本就直接报错，免得悄悄改错。

生成文件只带手机实际用到的只读表（几 KB 的数值表），不带游戏资源。
