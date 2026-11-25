# Changelog

## 0.4.6（versionCode 13）

- 修复（补丁 0083，通用，可向上游提交）：OpenGL ES 片段着色器默认精度改为优先使用 `highp float`（检测 `GL_FRAGMENT_PRECISION_HIGH`，不支持时回退 `mediump float`）。此前 `ShaderHeaderFrag` 对所有 GLES 设备写死 `precision mediump float;`，在严格按 FP16 执行片段采样的移动 GPU 上，对 `3072×6000` 字库图集（如 `sg-pc` 的 `FONT.PNG`）在下半区（`v > 0.5`）UV 量化步长可达约 3 像素，导致字形裁边与邻格串扰。已核对全部 `src/shaders/opengl/*_{vert,frag}.glsl`，无 uniform 精度冲突。
- 修复（补丁 0084，通用，可向上游提交）：OpenGL 纹理上传适配 `GL_MAX_TEXTURE_SIZE` 并补充诊断日志。`Renderer::Init()` 查询并缓存 `GL_MAX_TEXTURE_SIZE`（`<= 0` 回退 4096）并记录 `GL_RENDERER`、`GL_VERSION` 与 `GL_MAX_TEXTURE_SIZE`；`SubmitTexture()` 在尺寸未超限时走零开销原路径，超限时仅对超限轴做区域加权平均降采样（支持 `RGBA`/`RGB`/`UA8`/`U8`），避免 `3072×6000`（`FONT.PNG`）、`3648×7128`（`FontLBOutline`）、`3072×4224`（`ALBUM_THUM.DDS`）在上限 4096 的移动 GPU 上因 `glTexImage2D` 报 `GL_INVALID_VALUE` 导致渲染缺失或异常；同时在 `glTexImage2D` 与 `glGenerateMipmap` 后检查 `glGetError()`。
- 验证：MuMu 模拟器（Android 15，Adreno 640，**不是真机**），`sg-pc`（Steam 版 + 2018 汉化补丁），在原生上限（`32768`）与模拟 `4096` 上限（实测触发 `3072×6000 → 3072×4096`、`3648×7128 → 3648×4096` 降采样）双路径下验证标题、`SG00_01` 秋叶原站对话框、`BACKLOG` 与正常流程，零着色器及 GL 报错。真机未测。

## 0.4.5（versionCode 12）

- 修复（补丁 0081，通用）：调试模式只由设置里的开关打开。之前 profile 带 `GameFeature::DebugMenu` 的游戏（`cclcc`、`chlcc`、`mo6tw-pc`、`mo6tw` 等上游 profile）在设置里关掉调试模式后，左上角仍显示调试状态栏，速度、快进、`debug-cmd.txt` 等调试功能也仍然生效。MuMu 模拟器（不是真机）上验证：`DebugMode = false` 时不显示，`true` 时显示。
- 修复（补丁 0082，通用）：Bink 2 视频的声音。内置的 libbink2 把 KB2 文件的音轨按另一种格式（7 位量化表）解码，解出来是满幅杂音，而且比画面短。S;G0 的启动过场（`intro`）、OP、`anisama` 和 MOVIE 鉴赏，以及 S;G Steam 版里带声音的 Bink 2 视频（如 `IMV006`）都受影响。现在按 Bink 1 的音频格式解码，和 FFmpeg 的输出逐样本一致（`intro`、`OP`、`anisama`、S;G 的 `IMV006` 已比对）。Bink 1 视频走 FFmpeg，不受影响。设备上的声音待真机实听确认。

## 0.4.4（versionCode 11）

- STEINS;GATE 0 Steam 版（`sg0-pc`）标记为已适配：主应用从宿主 versionCode 11 起识别并启动它。
- 新增（补丁 0062，通用）：可选的渲染目标透明通道（`FramebufferAlpha`）。除屏幕外的渲染目标原来是 RGB；在渲染目标里拼好图再整体画到场景上的游戏（S;G0 的手机放大、系统菜单、存档画面）需要透明通道。默认关闭，其他游戏不变。
- 新增（补丁 0063，通用的存档格式＋仅 SG0 的挂钩）：MO6TWPC 存档条目可以带额外游戏数据，有这种条目的文件写成版本 3（条目末尾 u32 长度＋数据）；没有额外数据的文件仍写版本 2、逐字节与以前相同，版本 1／2 照旧读取，`sg-pc`、`mo6tw-pc` 的存档不受影响。S;G0 把手机状态（0x3ee0 字节）存在这里，读档时恢复。
- 新增（补丁 0064–0078，仅 TYN，除注明外）：S;G0 的系统画面按原版 Game.exe 移植，做法和手机一样（Ghidra 反编译后由 `tools/impacto/sg0/translate_phone.py` 机械翻译，引擎桥接手写）：右键系统菜单（画面缩进显示器、12 个圆形按钮）、SAVE／LOAD／QUICK LOAD（0064）、CONFIG 四页及滑块和角色语音（0065）、BACKLOG（0066 的 `IsEmpty`、可选 CC 回想遮罩和系统菜单绘制挂钩为通用代码；0067）、TIPS 列表／分页／正文（原版文字排版，0069–0070）、系统消息框（退出、回标题、读档确认，0071 的系统消息层挂钩为通用代码；0072）、手机和系统文字的完整颜色表（0073）、剧情中的 Amadeus 来电画面（0074）、EXTRA 的 CLEAR LIST（0076）、CG／SOUND／MOVIE 鉴赏（0075、0077、0078）。CG、BGM、TIPS 的解锁状态读写引擎存档系统里的对应数据。`sg0-pc` 里引擎自带的系统菜单、存档、设置、回想、TIPS 类关闭，对应图集改为剧本载入。
- 新增（补丁 0079，通用，可向上游提交；0080 仅 TYN）：可选的 profile 字段 `SaveData.WriteSystemDataOnBackground`。应用切到后台时（`SDL_EVENT_WILL_ENTER_BACKGROUND`，SDL 在主线程、两帧之间处理）同步写一次系统数据。手机上应用常在后台被直接杀掉，之前只存在系统数据里的内容（EXTRA 解锁之类的标志、游戏时间、设置、CG／BGM／TIPS 解锁）要等剧本下次写存档才落盘，被杀就丢了。有存档任务在跑时不写；存档里的系统数据还没被剧本应用（`LoadSystemData` 之前）时也不写，免得用初始状态覆盖掉玩家的存档。默认关闭，只有 `sg0-pc` 打开，其他游戏不变。MuMu 上验证：设标志 860 → 回桌面 → 强杀 → 重开，标题出现 EXTRA（修复前不出现）。
- 新增（补丁 0068，通用）：调试模式文件命令 `flag <n> <0|1>`、`var <n> <值>`、`unlock`（解锁 CG、音乐、TIPS；引擎 TIPS 表为空时按 profile 的 TIPS 数量全部解锁）。
- 工具：`tools/impacto/sg0/access_sizes.py`（capstone）扫描原版代码对每个全局变量的访问宽度，翻译脚本据此给 Ghidra 没定类型的全局补上类型；翻译脚本支持句柄与指针互转、指针全局、缺失参数补 0 等，修正表同步更新。
- 验证（系统画面）：MuMu 模拟器（Android 15，不是真机），`sg0-pc`（Steam 原版数据＋中文脚本），调试模式：系统菜单开关；SAVE 写入带缩略图、章节名、游戏时间、日期的存档，从系统菜单和标题读档并确认，读档后剧情继续、RINE 状态恢复；CONFIG 改 BGM 音量和语音跳过后重新打开仍保持；BACKLOG；TIPS 列表、分页、正文、滚动、点击和关闭；退出／回标题／读档确认框；B 线快进到“无限远点的牵牛星”结局和结局后的系统消息；Amadeus 来电（CONNECT）手机里显示红莉栖；CLEAR LIST；CG 鉴赏打开相册全屏看图、切图、返回；SOUND 解锁后播放、停止；MOVIE 播放 OP 全屏、右键返回。`profile-snapshot.py` 只有 `sg0-pc` 变化（BacklogMenu、OptionsMenu、SaveMenu、SystemMenu、Sprites、SpriteSheets，新增 FramebufferAlpha），其余 11 个 profile 不变。
- 新增（补丁 0060，仅 TYN）：S;G0 的手机和 RINE。原版手机模块（Game.exe 0x46b600..0x478000，90 多个函数）用 Ghidra 反编译后由 `tools/impacto/sg0/translate_phone.py` 机械翻译成 C++，原版全局变量放在模拟内存里保持原地址，绘图、文字排版、点击区域、输入等引擎接口在 `phoneshim.cpp` 实现，RINE 对话读取器（0x476d50、0x477040）和 `10:37` 指令手写移植。消息窗手机按钮打开，双指点击（右键）返回／关闭；RINE 回复可用箭头切换候选、点击发送；手机状态跟着调试快照保存。`sg0-pc` 的 GameSpecific 改为 `SG0`，手机图集登记为剧本载入的图集。
- 新增（补丁 0061，通用，可向上游提交）：调试模式可以用存档目录里的 `debug-cmd.txt` 下命令（`load`／`save`／`speed`／`skip`／`pause`），自动化测试不用再在触屏上拖 ImGui 窗口。见 `docs/debug-mode.md`。
- 验证（手机）：MuMu 模拟器（Android 15，不是真机），`sg0-pc`（Steam 原版数据＋中文脚本）：主屏、RINE、设定、壁纸、剧情中的 Amadeus 画面；序章真由理的 RINE 从选择回复到对话结束，关闭手机后剧情继续；回复等待中拍的调试状态能恢复整段对话。Amadeus 来电、存读档里的手机状态未验证。`profile-snapshot.py` 只有 `sg0-pc` 的 GameSpecific、SpriteSheets 两段变化，其余 11 个 profile 不变。
- 新增（补丁 0057–0059，S;G0 的数据与指令集仅 TYN，标题类的新字段为通用代码）：Steam 版 STEINS;GATE 0 的 profile `sg0-pc`（**适配中**，启动器里隐藏）。新指令集 `InstructionSet::SG0` 以 S;G 的指令表为基础，补上 S;G0 新增的条件调用、鼠标和键盘跳转（`00:53`–`00:59`）；标题画面按原版 Game.exe 移植（"0" Logo 动画、装饰、菜单、子菜单，SGHD 标题类加了一组可选字段，`sg-pc` 不使用）；对话框、名字和名牌按原版。存读档、设置等画面还没做。详见 `docs/steins-gate-0-steam.md`。
- 新增（补丁 0056，通用，可向上游提交）：两个可选的对话框字段。`FixedNameCenterOnHalfWidth`：固定位置、居中的名字以 `NamePos.x + MaxNameWidth / 2` 为中心（S;G0 的名字在屏幕正中）；`NametagType.CenteredTwoPiece`：名字两侧各一张图、随名字宽度对称展开的名牌。默认关闭，其他游戏不变。
- 修复（补丁 0055，通用）：内置 Bink 2 播放时设置 `SW_MOVIEFRAME` 和 `SW_MOVIETOTALFRAME`（FFmpeg 路径本来就设）。S;G0 靠比较这两个值判断视频快结束，之前总帧数是 0，开场 intro 刚开始就被截掉。
- 修复（补丁 0054，通用）：调试模式。保存状态前先建存档目录（从没存过档的游戏没有这个目录，状态写不进去、重启就丢）；跳过视频时把 `SW_MOVIEFRAME` 推到最后一帧，靠轮询帧数等视频结束的剧本（S;G0 世界线变动后的 `MACROSYS2` 标签 310）不再一直等下去。
- 识别规则：`profiles.json` 加 `sg0-pc`（`Game.exe`、`USRDIR/script.mpk`、`USRDIR/system.mpk`、`USRDIR/mpk_bg.lst`），`sg-pc` 加可选字段 `noneOf: ["USRDIR/mpk_bg.lst"]`，SG0 目录不再同时命中前作；`test-profiles.py` 检查 `noneOf` 的格式，并检查不同游戏的规则不会同时命中同一个目录。旧版主应用不认识 `noneOf`，会把 SG0 目录当作有歧义、不识别（不会再用 `sg-pc` 去启动它）。
- 测试：不依赖游戏数据的回归。`tools/impacto/profile-snapshot.py` 用检出里引擎自带的 minilua 按引擎的方式加载每个 profile，按顶层配置段记录哈希（`tools/impacto/profile-snapshots/`，共约 50 KB）；`test-profiles.py --source` 在本地和 CI 里逐个比对，`--diff-against <另一份检出>` 列出具体变化的行，有意的改动用 `--update` 更新。加 S;G0 前后 11 个已有 profile 的快照完全相同；故意改动共享的 `common/overlay.lua` 时 `sg-pc`、`mo6tw-pc` 等都被报出。规则写进 `AGENTS.md`「不依赖游戏数据的回归」。
- 工具：`tools/impacto/sghd/gen_widths.py` 多一个 profile 参数，可以给 `sg0-pc` 生成字宽表（S;G0 字体 `font_a.dds` 是 80 行）。
- 验证：MuMu 模拟器（Android 15，不是真机）。`sg0-pc`（Steam 原版数据＋中文脚本）从标题、新游戏一路到 `SG0_B01_12`；`sg-pc`（Steam 原文件＋2018 汉化）回归标题、按下开始、菜单、LOAD 子菜单、新游戏、第一次世界线变动，与改动前一致。真机未测。

## 0.4.3（versionCode 10）

- 新增（补丁 0051，通用）：内置 Bink 2 解码。`FFmpegPlayer` 遇到 Bink 2（`KB2*`）文件交给新的 `Bink2Player`，用 [libbink2](https://github.com/raynorpat/libbink2)（LGPL-2.1+）解码视频与 Bink Audio 2 音频；KB2g 起的透明通道按 FFmpeg Bink 2 补丁补上；视频时钟以帧时间为准，有声音时跟随声音（声轨比画面短时不再卡在最后一帧）。`sg-pc` 只用游戏原文件就能播放全部视频，包括世界线变动的辉光管动画，不再需要 `convert_bink2.py` 转换。发行包的许可证合集附上 libbink2 的 LICENSE。
- 修复（补丁 0052，仅 TYN）：`sg-pc` 的视频标志改为原版 Game.exe 的 1851（播放中）与 2492（可取消）。之前沿用通用表的 1823，世界线变动的剧本（MACROSYS2 标签 375）一开始就认为视频结束，辉光管动画只闪一下就被停掉。
- 新增（补丁 0053，通用）：调试模式，给适配新游戏用（`[CommonSettings] DebugMode`，宿主设置 `debugMode`，默认关闭）。触屏三指同按打开调试菜单的「适配工具」：逻辑速度 x1–x64、暂停与逐帧、强制快进（未读文字与视频也跳过）、跳过当前视频、每句自动快照与按句回退（回到选项可以重选）、跨启动保存的状态、跳到任意剧本的任意标签、重开当前剧本、一键解锁 CG／音乐／TIPS；界面中英可切换。用法见 `docs/debug-mode.md`。
- 验证：MuMu 模拟器（Android 15，不是真机）上用 `sg-pc`（Steam 原文件＋2018 汉化）和 `mo6tw-pc-zhs` 两个游戏实测上述功能；`sg-pc` 的标题（带透明通道）、叠加特效与世界线变动视频 `imv007` 完整播放。真机未测。

## 0.4.2（versionCode 9）

- 新增（补丁 0049–0050，仅 TYN）：`sg-pc` 标题 EXTRA 的 CLEAR LIST、CG LIBRARY、SOUND LIBRARY、MOVIE LIBRARY 按原版 Game.exe 移植（布局、点击区、解锁规则、CG 全屏查看的缩放与拖动、音乐的四种播放模式）。之前这四个画面没有实现，进入后剧本停在看不见的菜单里，标题画面不能再操作。MuMu 上用导入的全通关存档逐个打开验证。
- 修复（补丁 0048，通用）：屏幕色层的数量、间隔与第二层改由 profile 指定；`sg-pc` 有三个、间隔 10（原版 0x428d50）。之前只画两个、间隔 7，世界线变动时的色调不显示。
- 修复（补丁 0047，通用）：sprite sheet 可以检查指定格子的墨迹是否居中，字体对居中的格子用整个字宽。`sg-pc` 用它处理汉化字体里居中的全宽间隔号（id 226），原版字体不受影响。
- 文档：README 与 `docs/steins-gate-steam-sghd.md` 标为「已适配完成」。

## 0.4.1（versionCode 8）

- 新增（补丁 0045，仅 TYN）：`sg-pc` 时间跳跃的翻牌钟（原版 0x41a140 / 0x41a960 / 0x418d60）。之前只读 `10:3A` 的操作数，时间跳跃时只有背景视频。现在月、日、星期、时、分按原版翻牌倒数，从 3 倍缩放淡入。原版例程在模拟器里运行，与移植逐帧比较，剧本表里的全部时间跳跃画出的精灵都相同；MuMu 上第 6 章的时间跳跃验证过。
- 修复（补丁 0046，通用）：隐藏的文本框总能重新显示。文字在隐藏时不会继续显示，所以在一句话显示完之前隐藏，就再也达不到「可以切换隐藏」的条件，场景一直等下去（MuMu 上第 6 章 `SG06_05` 的电话场景遇到）。
- 修复（补丁 0042，仅 TYN）：`sg-pc` 的手机能用带下划线的词回复邮件（原版的模式 27，0x456c30；鼠标／触摸指向词即选中，按键在可见的词之间移动并滚动正文）。之前不能选词，邮件链在第 5 章就断了，第 10 章只能进真由理线，牧濑线和真结局都到不了。MuMu（**不是真机**）上用汉化数据从第 5 章开始只靠回复邮件走到真结局：第 10 章进牧濑线（`SG10_10C`–`SG10_12C`），邮件 386 回复后进第 11 章，`SG11_08` 之后回到标题。
- 修复（补丁 0041，仅 TYN）：读档后不再播放存档时残留的循环视频（标题／时间跳跃的背景视频一直盖在画面上）；优先级 10000 的视频（世界线变动的辉光管动画）画在对话框与日期之上，和原版一样播放时只看得到视频。
- 修复（补丁 0043–0044，通用）：内存泄漏。每写一行日志就漏掉这一行的缓冲区（上游 `ImpLogImpl` 用 `malloc` 分配后没有释放）；开着详细日志时每分钟漏几 MB，2 GB 内存的 MuMu 长时间游玩后被系统杀掉。背景与立绘上传到显卡后也释放内存里的像素副本。MuMu 上修复后游玩 4 分钟堆只增长约 2 MB（之前每 30 秒约 7 MB）。

## 0.4.0（versionCode 7）

- 新增（补丁 0033–0037，S;G 的数据仅 TYN，`SGHD` 指令集文件为新文件）：`sg-pc` 的手机按原版 Game.exe 做出来（之前 `10:37` 只是跳过操作数的桩，需要打电话、发邮件的剧情点走不通，各章结尾的分歧只能进角色结局）。逻辑取自原版的手机主例程 0x453800 与各画面例程（`10:37` 的邮件状态位、跳转、可通话／可发邮件的联系人、收发件箱、通讯录、拨号盘、来电、附件、铃声、`10:38` 附件文本页）；绘制取自各画面的绘制例程（图集 `PHONE*.DDS`、`PACG`、`PWCG`）；鼠标／触摸的点击区来自原版的表 0x52ea58（判定 0x433040）；左上角的小手机（0x45a9a0）在有新邮件时闪烁，点它打开手机（原版的鼠标模式，标志 2363，0x434d40）；宿主的屏幕按键第一页加了 Z（L2／手机）键。手机的按键不再同时隐藏文本框。MuMu（Android 15，**不是真机**）上，原版英文数据和汉化数据都验证了：第 1 章拨号盘输入 120#、第 6 章结尾发送准备好的邮件（不进铃羽结局）、第 7 章结尾发送 D-mail（不进菲莉丝结局）、第 8 章结尾给登记的联系人打电话（不进琉华结局），之后进入第 9、10 章。
- 新增（补丁 0038–0040，仅 TYN 与一处通用容错）：`sg-pc` 的视频（`USRDIR/movie/1920x1080`，按原版程序 0xd42698 的表给文件编号，文件夹挂载支持固定的文件编号）；FFmpeg 解不了的视频（Bink 2）不再让脚本一直等待或崩溃，直接跳过；`10:3A`（时间跳跃的日期）读完它的六个表达式（之前当作 CC 的 `YesNoTrigger` 解析，第一次时间跳跃崩溃）；时间跳跃结束后清掉标志 2472（之前画面一直黑着）。时间跳跃的日期计数动画还没画。
- 新增（宿主工具，不进 APK）：`tools/impacto/sghd/convert_bink2.py` 用你自己游戏目录里的 `bink2w32.dll`（32 位小程序 `bink2dump`，源码在 `tools/impacto/sghd/bink2dump/`）把 24 个 Bink 2 视频转换成 H.264／AAC，文件名不变，替换到 `USRDIR/movie/1920x1080` 后引擎就能播（世界线变动的辉光管动画 `IMV*`、标题背景、时间跳跃背景）；`tools/impacto/sghd/import_steam_save.py` 把 Steam 版 `SAVEDATA.DAT` 的系统数据（已读标记、CG／BGM／TIPS 解锁、通关标志）并入 `sg-pc` 的存档，存档格保留。MuMu 上转换后的标题视频能播，导入后已读文本能按「只跳过已读」快进。
- 修复（宿主）：游戏界面的 `configChanges` 补全（语言、密度、键盘、导航、界面模式等）。之前系统语言列表变化等配置变化会让 Android 重建 Activity，SDL 不能重建，游戏直接退出（MuMu 上实际遇到）。
- 汉化数据：`sg-pc` 用 2018 年的汉化补丁数据（`script.mpk`、`system.mpk`、`bg.mpk`、`manual.mpk`）验证过：字体图集只替换了汉字格子、格子数不变；汉化的 `CLEARLIST`／`CONFIG`／`DATA01`／`MOVMENU` 是同尺寸的 PNG（扩展名仍是 `.DDS`），引擎按内容识别。已知：汉化字体里 id 226（间隔号）变成全宽，字宽表仍按原版的 32。

- 新增：`engine/impacto/profiles.json` 打包进宿主 APK（资产 `tyn/profiles.json`），Tyranor Next 可以从已安装的宿主读取游戏识别规则，宿主新增 profile 后主应用不用发版就能识别。为此给所有 profile 补全了 `detect`（上游 profile 的条目取自主应用现有的目录表），并新增 `unsupportedLayouts`：「像 MAGES. 但没有 profile」的目录布局（Windows／Steam 版 `USRDIR/` 里的 `script.mpk` + `system.mpk` → 尝试 `sg-pc`，`data/` 里的 `script.cpk` + `system.cpk` → `mo6tw-pc`，根目录 `script.mpk` + `system.mpk` + `bgm.mpk` → `cclcc`，`script.cpk` + `system.cpk` + `bgm.cpk` → `chlcc`；至少两个档案，单个常见档名不算，免得收进其他用 CRI 档案的游戏），主应用把这类目录列为「暂不支持」并允许尝试运行。发布工作流核对 APK 里的资产与仓库文件逐字节相同；`test-profiles.py` 检查每个 profile 都有规则、路径格式与 `tryProfile`。宿主版本随本版发布（0.3.1 没有单独发布）。
- 文档：README 精简为入口、仓库规则、支持的游戏、与 Tyranor Next 的约定和构建发布，验证细节留在 CHANGELOG 与 `docs/`；`AGENTS.md` 增加 `profiles.json` 契约的维护规则。
## 0.3.0（versionCode 5）

- 新增（补丁 0032，S;G 的布局仅 TYN，TIPS 数据与界面类为通用）：`sg-pc` 的 TIPS 按原版 Game.exe 做出来（之前 TIPS 系统为 None：TIPS 从不解锁，画面空白，只能按返回）。数据格式、排序、布局与行为取自原版的 TipsDataInit 0x43e100、TipsInit 0x43f050、绘制 0x43e440 和主例程 0x43f720。新的 `TipsSystemType.SGHD` 读 `_TIPS` 的两个数据标签（条目；字母与分类表），按读音排序编号，每个分类按字母分组；`TipsDataInit` 不再丢弃第二个标签。新的 `TipsMenuType.SGHD`：分类（空的为蓝色）加「New」「Unread」两个列表和 NEW 标记；分类内按【字母】分组，编号、名称（未读为绿色、未解锁为灰色「???」）；右侧显示编号、名称、副标题、标签和正文（TIPS 文本模式，裁剪，L1／R1 翻页，滚轮）；返回在条目列表回到分类，在分类里交给脚本关闭。MuMu（Android 15，原版英文数据，**不是真机**）上：从标题 EXTRA 和游戏内系统菜单打开，分类列表与原版截图一致；继续游戏后解锁的 TIPS 带 NEW 标记，「New」列表、条目正文、翻页、返回正常。已知：TIPS 的解锁状态和其他系统数据一样在存档或退出 CONFIG 时写盘。
- 构建：固定的上游 impacto 提交从 `31bbd61` 升到 `415af23`（上游 19 个提交：覆盖层的 toast 通知、更新检查、成就通知移到覆盖层、CHLCC 的 TIPS 与快速存档修复）。补丁分支直接变基，没有文本冲突；两处跟随上游的改动：`mo6tw-pc*`、`sg-pc` 的 profile 改为包含上游新的 `common/overlay.lua`（上游删除了 `common/achievementnotification.lua`，并入原补丁 0010、0017）；新增补丁 0031（通用修复，放在系列末尾以保持已有补丁编号，可向上游提交）：上游在每个游戏启动后都推送「打开覆盖层」提示并启动更新检查，而提示用的字体只在 profile 带 `GameFeature.Overlay` 时才配置，其他 profile（cc、mo6tw、rne、darling、dash、mo8、`sg-pc`、`mo6tw-pc*` 等）启动约 2 秒后空指针崩溃；现在只对带覆盖层的游戏推送。CI 检查（`verify-upstream`、`test-patch-series`、`test-profiles` 等）通过，dev 构建通过；MuMu（Android 15，**不是真机**）上 `sg-pc` 的标题、读档、系统菜单、CONFIG、HELP、退出确认框与 `mo6tw-pc-zhs` 的标题、New Game、系统菜单正常。
- 文档：新增 `AGENTS.md`，README 增加「仓库规则」：上游代码只能以补丁形式修改，补丁要便于跟随上游，定期同步上游。
- 新增（补丁 0030，S;G 的布局仅 TYN，界面类为通用）：`sg-pc` 的系统消息框（读档确认、返回标题、退出游戏等）按原版 Game.exe 做出来，替换之前用 MO6TW 消息框加估计位置的做法。数据来自原版的消息框绘制 0x43d470、布局 0x43da50（宽度、选项点击区）、输入 0x43dc00、SystemMes 处理 0x464d00（两个框，每帧淡入淡出 16）和画面绘制 0x46e650。新的通用界面类 `SysMesBoxType.SGHD`：框的三块、文字和选项位置、高亮、变暗都由 profile 描述。照原版：内容宽度取最长消息、选项总宽或最小值；`DATA01` 三块拼框，中间拉伸；消息左对齐，带左上、右下两份黑色描影；选项右对齐排在一行，选中的项下面拉伸高亮条；一开始没有选中项，左右循环，没有选中时按确定只选第一项，返回把光标移到第二项（不关闭），鼠标／触摸悬停选项、点击确定。SystemMes：S;G 的模式 10..17 是原版第二个（全局）消息框的模式 0..7（退出游戏用它），以前当作未知模式、没读字符串操作数，脚本线程崩溃；现在打开单独的框，屏幕盖 3/4 不透明度的黑，选择写到 `SW_SYSSEL + 1`，与原版一致（`UI::SysMesBox` 加了 `Global` 标记，只有 SGHD 指令集用）。MuMu 上：读档确认、返回标题、退出游戏与原版截图布局一致，确定先选再确认，返回移到取消，点取消关闭，退出游戏变暗且不再崩溃；memo06 标题不变。
- 新增（补丁 0029，S;G 的布局仅 TYN，界面类为通用）：`sg-pc` 的标题画面按原版 Game.exe 做出来，替换之前用 CC 标题类加估计位置的做法（菜单原来在左边，原版在右边）。数据来自原版的标题绘制分派（按 `SW_TITLEMODE`，0x4414f0）、主列表 0x4411e0、子列表 0x440600／0x440be0／0x441080、装饰 0x4407f0、Press Enter 0x4422e0、按键提示 0x436030、输入例程 0x441650 和 0x52bf20 的点击区表。新的通用界面类 `TitleMenuType.SGHD`：主项、子列表（可按标志切换）、装饰、提示、位置和时序都由 profile 描述。绘制照原版：模式 0 从黑淡入，1 Press Enter 64 帧闪烁，2 快速闪烁，3 菜单随 `SW_TITLEDISPCT`×8 淡入、从右侧 192 像素移入，4 背景和菜单淡入，5 同 3（在标题上打开的画面下面）；蓝图装饰隔帧绘制，其中三块随机显隐，一条随机长度。输入照原版：上下循环（从“无”到第一项），鼠标／触摸悬停选项（鼠标模式下指针不在项上时无选中项），LOAD、EXTRA 用 32 帧打开子列表（标志 860 设置后 EXTRA 有五项，否则只有 CLEAR LIST、TIPS），子列表打开时只有它的项收输入，返回关闭；选中的项闪烁 64 帧后再设 `SW_TITLECUR1` 和 `SF_TITLEEND`，期间脚本在 TitleMenu(Main) 里等待，不会处理这些按键。原版标题上的卫星是 Bink 2 视频，本引擎不能播放。MuMu 上：与原版截图一致（主列表、LOAD／EXTRA 子列表、逐步按键导航、提示条），点击打开子列表、返回关闭，LOAD 打开读档画面并能返回，CONFIG、HELP 能打开；memo06 标题不变。
- 新增（补丁 0028，S;G 的布局仅 TYN，界面类为通用）：`sg-pc` 的 HELP 画面按原版 Game.exe 做出来，替换 0023 里“选中直接退出”的临时兜底。数据来自原版的绘制例程 0x4351f0、输入例程 0x435640、Help(Init) 0x4355a0 和 0x52b670 的点击区表；两页说明图就是 `manual.mpk` 的 PAGE1（键盘与鼠标）、PAGE2（手柄），汉化数据自带汉化图。新的通用界面类 `HelpMenuType.SGHD`：页、页码、页签、按键提示都由 profile 描述。行为照原版：脚本子菜单为 HELP（11）时显示，不透明度 = `SW_SYSSUBMENUCT`/32 × `SW_SYSSUBMENUALPHA`/256，打开时页面从 x = -400 移入；每次从第 1 页开始；E／Q（R1／L1）、鼠标滚轮和页签翻页，新页盖在旧页上滑入（16 帧，每帧 48 像素，同时淡入；下一页和页签从左边、上一页从右边），滑动时不收输入；悬停的页签（否则当前页的页签）闪烁；返回抬起 `SF_SUBMENUEXIT` 和 `SF_MANUALLOAD_END`。原版只在启动器里配置过手柄时才在 PAGE2 上写按键名，这里没有手柄配置，所以和原版未配置时一样。MuMu 上：从标题和游戏内系统菜单打开都与原版截图一致，点页签和 E／Q 翻页带滑动，Backspace 和双指返回回到标题／系统菜单，再次打开从第 1 页开始。
- 新增（补丁 0027，S;G 的布局仅 TYN，界面类为通用）：`sg-pc` 的 CONFIG 画面按原版 Game.exe 做出来，替换 0023 里“选中直接退出”的临时兜底。三页（基本／文本、声音、各角色语音）的布局、图块、数值范围与步长、默认值都从原版程序读：各页绘制例程（0x438ef0、0x438240、0x438a60、页签 0x43b490）、输入例程（0x439b00 起）、默认值（0x438030 起）；文字是 `CONFIG.DDS` 图集的一部分，汉化数据就显示汉化文字。新的通用界面类 `OptionsMenuType.SGHD`：页、行（开关、滑块、单选、角色语音）、页签全部由 profile 描述，代码里没有布局。行为照原版：脚本淡入子菜单 5 时显示，完全显示时独占输入，返回抬起 `SF_SUBMENUEXIT` 并写系统数据；每页各有光标，初始无光标；上下循环；Q／E 和页签翻页，32 帧横向滑动；滑块在打开时的位置留一个半透明点；鼠标／触摸：悬停或点击移光标，点击切换，拖动设滑块，点击区用原版的表。窗口模式和分辨率在这里没有意义，显示固定状态（全屏、1920x1080）。CC 标题菜单在别的画面拿着菜单焦点时不再处理输入（它先于选项画面更新，吞掉了点击）。MuMu 上：从标题和系统菜单打开都与原版截图一致，翻页、点击、拖动、返回、再次打开正常，改过的设置重启后保留；memo06 不变。
- 改进（补丁 0025，S;G 布局仅 TYN，存档页格数为通用改动）：`sg-pc` 的存档／读档／快速读档画面改用原版 Game.exe 的布局，不再用估的值。数值来自原版的存档画面绘制代码（约 0x43b661，绘制函数 0x432230；原版按 1280x720 计算、乘 1.5 绘制）：每页 8 格（2 列 x 4 行，0022 估的是 6 格），格子卡片是图集自己的 (1921.5, 1.5, 789 x 166.5)，画在 x 114／982.5、y 130.5／321／511.5／702；缩略图 240 x 135 在卡片 +(15, 15)；NO DATA 是图集的 (2713.5, 1.5, 240 x 135)；共 6 页。MO6TWPC 存档画面的每页列数、行数改为可选 profile 字段 `EntriesPerRow`／`RowsPerPage`（默认 2 x 3，memo06 PC 不变）。格子里的文字位置、锁图标、页签（原版是 y 934 的 85 x 36 页签）仍是估的。MuMu 上：S;G 读档画面 8 张原版卡片、页码 1 / 6，读档正常；memo06 读档画面不变。
- 改进（补丁 0026，S;G 布局仅 TYN，系统菜单类的扩展为通用改动）：`sg-pc` 的系统菜单改用原版布局和动画：面板 (1261.5, 37.5, 82.5 x 750) 在 (93, 163.5)；每行图标 78 x 61.5 在 (96, 178.5 + 57 i)，普通灰色、聚焦白色；聚焦行的文字从面板后面滑出（约 8 帧）；整个菜单随 `SW_SYSMENUALPHA` 从左侧滑入 192；点击区域用原版的表（321 x 57 的行）。MO6TW 系统菜单类新增可选字段 `MenuEntriesLabelSprites`／`MenuEntriesLabelX`／`MenuEntriesLabelRevealDuration`、`SlideInDistance`、`MenuEntriesHoverBounds`，不设时行为不变（memo06 PC）。原版对不可用项用的暗色图标还没有。MuMu 上：位置与原版一致，文字滑出，SAVE／CONFIG／CLOSE MENU 点击可用，从 SAVE 返回回到菜单；memo06 系统菜单不变。
- 修复（补丁 0023，仅 TYN）：`sg-pc`（STEINS;GATE Steam）从系统菜单打开的存档／读档／快速读档画面按返回退不出来，CONFIG 和 HELP 会卡在看不见的画面后面。原因：`10:3F` 是原版引擎的「菜单打开／关闭」信号（脚本在每个画面前后成对发：3/4 存读档、5/6 TIPS、17/18 系统菜单、21/22 选项、23/24 帮助），存档画面按返回时脚本只把 `SW_SYSSUBMENUCT` 数回 0 就返回，`SW_SYSSUBMENUALPHA` 留在 256，跟着这个值显示的 MO6TWPC 存档画面一直盖在系统菜单上；现在类型 4 会把它清零。CONFIG／HELP 的脚本等 `SF_SUBMENUEXIT`，只有原版的选项／帮助画面会抬起它；S;G 的这两个画面还没有，所以子菜单完全淡入后就抬起退出标志（与 memo06 PC 选项的兜底同一思路），脚本回到系统菜单或标题。之前说的「脚本在轮询 `00:53`」是误判：S;G 只在 Logo 画面用 `00:53`。只改 SGHD 的指令文件（`inst_sghd.h`、`opcodetables_sghd.h`）。MuMu 上：SAVE、LOAD、QUICK LOAD 打开后按返回回到系统菜单，CONFIG、HELP 回到系统菜单（从标题进入则回到标题）。
- 修复（补丁 0024，通用：`cc`、`chn`、`sg-pc` 用的 CC 标题菜单）：点 CONTINUE／LOAD 或 EXTRA 只记下子菜单，显示和隐藏的调用被注释掉了，子菜单项从来不出现也选不了。现在点它会显示子菜单并把焦点移到第一项，返回或选中子菜单项后收起并把焦点还给打开它的那一项（这一下返回不传给脚本）。新增可选 profile 字段：各按钮写入 `SW_TITLECUR1` 的值（`ConfigId`、`HelpId`、`LoadId`、`QuickLoadId`、`TipsId`、`LibraryId`、`EndingListId`）和两个子菜单所在的行（`ContinueSubRow`、`ExtraSubRow`），默认值就是原来的常量，不设的 profile 行为不变。`sg-pc` 设成 S;G 标题脚本的编号（0 START、10 QUICK LOAD、11 LOAD、20 CLEAR LIST、21 CG LIBRARY、24 TIPS、30 CONFIG、40 HELP；原来点 CONFIG 会打开 CLEAR LIST，LOAD 两项是反的），子菜单在主菜单项所在的行横向排开。MuMu 上：标题 LOAD 展开 LOAD／QUICK LOAD，LOAD 打开读档画面，返回回到标题，读一格后继续游戏。
- 改进（补丁 0022，仅 TYN）：`sg-pc`（STEINS;GATE Steam）的系统菜单、存档与读档画面、系统消息框，并打开存档。S;G 的脚本用的协议与 memo06 PC 已经在用的类一致，所以不写 S;G 专用的 C++：系统菜单用 `SystemMenuType.MO6TW`（`SW_SYSMENUALPHA`／`SW_SYSMENUCNO` 就是 S;G 脚本用的 2143／3338，十二个入口是脚本 `JumpTable` 的顺序，精灵量自 `DATA01.DDS`），存档用 `SaveDataType.MO6TWPC`，存读档画面用 `SaveMenuType.MO6TWPC`（`SAVEMENU`／`LOADMENU`／`QLOADMENU`），确认框用 `SysMesBoxType.MO6TW`（`SYSMESSWINDOW`／`GSYSMES` 是全透明的 128x128，盒子用 `DATA01` 里一块暗色区域拼）；`charset.lua` 补了引擎自己排版文字（格号、日期）需要的 ASCII→字形表。两处向后兼容的通用扩展：MO6TW 系统菜单认 `MenuEntriesHighlightedSprites`（每个入口各有聚焦精灵，hover 区域覆盖两张），MO6TWPC 存档菜单认可选的 `SaveBackgroundSprite`／`LoadBackgroundSprite`／`QuickLoadBackgroundSprite`；memo06 PC 的 profile 不设这些字段，行为不变。MuMu 上：菜单键打开十二个图标的系统菜单，聚焦的一行显示名称，BACK LOG／CLOSE MENU 可用；SAVE 存一格后显示缩略图、游玩时间、日期；LOAD 选格后弹出确认框，确认后回到存档的那一句。未做：从存档画面按返回退出（已由补丁 0023 修好；当时误判为 `00:53`）、QUICK LOAD／TIPS／CONFIG 等界面、手机、格子高亮与 PREV／NEXT 的美术（图集里没有）。
- 改进（补丁 0021，仅 TYN）：`sg-pc`（STEINS;GATE Steam）的日志、字体和换行。日志：S;G 的脚本经 `MesRev`（`Unk0110` 模式 0..5）和系统循环里对 `PADcustom[12]` 的 `KeyOnJump` 轮询打开日志；`InstMesRev` 的显示／隐藏原来只对 MO6TW／MO6TWPC 调用，现在 SGHD 也调用，`UpdatePADInput` 对 SGHD 的向下轻扫／滚轮另外抬起 `PADcustom[12]`（引擎本来只合成 F2 键，S;G 不读它），profile 用量过的 `BACKLOG.DDS`（面板与标题、滚动条轨道与滑块、语音图标）。字体：profile 沿用了 CC 的字宽表，圆形拉丁字母（`o`、`O`、`?`）被裁掉右边；改用 `tools/impacto/sghd/gen_widths.py` 从字体图集生成的字宽（`font-widths.lua`，id 1..226 按墨迹右边缘加 3，空格 16，其余 48，em 宽 48）。换行：两份拉丁字母和数字在 `charset.lua` 里标成 `Alphabet`，单词不再从中间断开。MuMu 上序章前半的对话字形、间距与换行正确，向下轻扫打开日志（章节标题、人名、台词、语音图标、滚动条）；人名在对话框右下是脚本的固定位置模式，不是排版错误（此前的说明有误，已在文档里更正）。
- 新增（宿主，所有 profile）：屏幕按键与虚拟鼠标。纯触屏设备原来够不到强制快进、快速存档、系统菜单、方向键与 F 键（这些只有键盘／手柄入口；触摸手势只有点击、两指轻点／捏合、上下滑、左右滑和长按，不好记也容易误触）。`TouchControls`（宿主自己的 Java，不改引擎、不动补丁系列）在游戏画面上放一个可拖动、会淡出的小悬浮球，点开是一条按键条，**按键直接显示键位名**（Enter、Space、Bksp、Del、E、Q、Ins、1、F8、Esc、Ctrl……），下面一行小字写引擎默认键位里的功能；分页：常用、方向（↑↓←→、WASD、Home/End/PgUp/PgDn、Tab）、F1–F12、A–Z、0–9 加 Shift/Ctrl/Alt、鼠标（左右键、滚轮）。可以横向或竖向展开；设置里可调透明度、大小、展开方向、键位提示、空闲淡出、自动收起、重置位置。另有一个很小的虚拟鼠标箭头：拖动移动（引擎看到的是真鼠标，悬停高亮和点击都有效），点它是左键，长按是右键。按键与鼠标都经 `SDLActivity.onNativeKeyDown/Up`、`onNativeMouse` 送入 SDL，所以自带键位表的 profile 也能用。`SETTINGS` 增加宿主专用字段 `touchControls`（`false` 则整个关闭）。MuMu（`mo6tw-pc-zhs`、`sg-pc`）上验证了悬浮球、横竖展开、各页、自动／日志／菜单／返回／F8 快速存档／按住 Q 强制快进、滚轮下开日志、虚拟鼠标拖动／悬停／点击／长按右键、透明度与大小滑块；没有真机验证。
- 修复（宿主测试）：`ImpactoRequestTest.profileListMatchesTheAppCatalog` 还断言 10 个 profile，加了 `sg-pc` 之后该是 11 个。
- 修复（补丁 0015，仅 TYN）：PC 版 Memories Off 6 的日志（Backlog）原来打不开：向下轻扫会跑完 PC 脚本的日志流程（`MesRev` 的 DispInit 再每帧 Main，`SW_SYSSUBMENUNO` 为 1），但什么都不画，脚本在看不见的画面后面等退出标志。两个原因：`InstMesRev` 只对 `InstructionSet::MO6TW`（PS3）调用 `BacklogMenuPtr->Show()`／`Hide()`，PC 的指令集是另一个值；`profiles/mo6tw-pc/hud/backlogmenu.lua` 沿用了 PS3 的 `DrawType` `ExtrasScenes`，而 PC 脚本把日志当系统菜单的子菜单，开着时画的是 `SystemMenu` 层。修复后在 MuMu（`mo6tw-pc-zhs`）上向下轻扫打开 BACKLOG 画面（日期标题、人名、已读台词），两指轻点关闭后继续下一句。条目间距、滚动条与高亮条仍是 PS3 配置放大 1.5 倍的近似值。
- 实验（补丁 0017–0020）：Steam 版 STEINS;GATE（`sg-pc`）。它与 Chaos;Child（PC）是同一代引擎，所以新增 `InstructionSet::SGHD`（CC 表加几处覆盖：`00:4C`、`10:1B`、`10:3F`、`10:37`、`10:38`）和一个 profile，标题菜单复用 CC 的标题菜单类并按 `TITLE_CHIP` 图集重新量坐标。把参考反汇编器的指令长度和引擎实际执行逐条比对（启动到序章约 23 万条指令）没有其他操作数不一致。MuMu 上实测：Logo、标题、主菜单、START、序章背景与对话文字。没有存档（`LoadSystemData` 对 SGHD 报告 OK）；HUD 精灵、系统菜单、日志、TIPS、名牌位置仍是占位；语音／BGM／序章之后没有验证。宿主白名单与 `profiles.json` 增加 `sg-pc`；主应用的目录检测还没有。
- 修复（补丁 0018，可向上游提交）：DDS 加载器把解析状态放在文件级全局变量里，多个加载线程同时解码时互相覆盖，squish 写越界、进程 SIGSEGV（Android 上 S;G 的 DXT5 系统图集会触发）；改为 `thread_local`。
- 修复（补丁 0016，仅 TYN）：PC 版日志画面的语音图标、滚动条滑块和滚动条轨道改用在 `backlog.png` 上量出来的坐标（PC 图集不是 PS3 图集的 1.5 倍：原来的坐标画出黑条、不在图集上的滑块，轨道还指到 2048 宽图集的 x=2250）。语音条目前现在有喇叭图标，右侧有带圆珠滑块的轨道；条目间距与高亮条仍是近似值。
- 修复（补丁 0014，仅 TYN）：PC 版 Memories Off 6 的「Option」（系统菜单与标题菜单都有）原来点了没有任何可见效果，脚本还会在看不见的选项画面后面一直等 `SF_SUBMENUEXIT`，要按返回才能出来。原因是 PC 脚本通过 CC 风格的子菜单变量（`SW_SYSSUBMENUNO` 为 5、`SW_SYSSUBMENUALPHA` 0→256）打开它，从不碰 PS3 版选项菜单依赖的 `SW_OPTIONALPHA`。现在 `InstructionSet::MO6TWPC` 下子菜单渐入完成就立即给出退出标志，脚本照常渐出并回到系统菜单。PS3 布局与 PC 图集对不上，所以没有把它显示出来；PC 专用的选项画面仍是缺口。
- 文档：新增 `docs/steins-gate-steam-sghd.md`（Steam 版 STEINS;GATE 与 `sg-pc` 的现状、与 Chaos;Child 的关系、怎样发现不同的操作码、已知缺口）以及读 MPK v2 的小工具 `tools/impacto/sghd/mpk_tool.py`。
- 构建：固定的上游 impacto 提交从 `ba0b6e0`（PR #580）升到 `31bbd61`（PR #582，只改 `src/games/cclcc/mapsystem.cpp`，与补丁系列无交集）。补丁分支直接变基，13 个补丁逐字节不变（`source-lock.json` 里的补丁 SHA-256 一个都没变，只改了 `impacto.revision`）；`verify-upstream.py --series-only` / `--patched`、`test-patch-series.py`、`test-profiles.py` 通过，dev 构建通过，MuMu（Android 15，x86_64 + arm64 转译）上 `mo6tw-pc-zhs` 能进标题、New Game、第一段对话与选项。这是补丁系列「只加文件、少改上游文件」策略的一次实际演练。
- 文档：主 Tyranor Next 应用识别 PC 版目录布局（`game.exe` + `data/*.cpk`；[Tyranor-Next#192](https://github.com/Weiss-UltimateSavior/Tyranor-Next/pull/192)，随该 PR 合入并发布的主应用版本生效），添加游戏目录并扫描后按应用界面语言选 `mo6tw-pc-zhs`、`mo6tw-pc` 或 `mo6tw-pc-zht`，只对这三个 profile 要求宿主 0.2.0 及以上。README 里「主应用尚不识别 PC 版目录布局」的说明相应改写；0.2.0 条目里的同一句话是该版本发布时的状态，保持原样。无代码改动。

## 0.2.0（versionCode 4）

- 来源策略从「只用未改动的上游」改为「固定上游提交 + 本仓库经审计的补丁系列」：补丁放在 `engine/impacto/patches/`（`NNNN-*.patch` + `series`），
  SHA-256 记录在 `source-lock.json` 的 `patches`；检出必须恰好等于「固定提交 + 系列」，构建、Gradle 与两个工作流都会校验。
- 补丁系列的内容：通用引擎修复（`SetStringIp` 的缓冲检查、MSB／脚本字符串缓冲的判别、无表的指令组容错、口型表越界检查）、存档文件任务的串行化（同一时刻只运行一个，后到的排队，写入前在主线程拍快照）、两个新的 profile 开关
  （`Game.VoiceTableLittleEndian`、`Dialogue.NameInsideNametag`）、**MO6TWPC 指令集**（Windows／Steam 版 Memories Off 6 T-Wave 的脚本指令）、
  PC 版 SystemMes 布局与标题模式编号，以及 **`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht` 三个 profile**（日文、简体、繁体；PC 版同时带三套 `mesNN.cpk`，语言由使用者选）与它们在 `gamedefinitions.lua` 里的注册。
- 宿主接受新 profile `mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`；`engine/impacto/profiles.json` 以机器可读形式列出全部可启动 profile（来源、名称、语言、检测文件提示），
  `ImpactoRequestTest` 校验 `ImpactoRequest.PROFILES` 与它一致，`tools/impacto/test-profiles.py` 校验 PC 变体的 `Dir` 与目录名。
- 工具（`tools/impacto/`）：
  - `apply-patches.py`（只接受干净的固定提交或已恰好应用的检出，失败即停）、`verify-upstream.py --patched`（检出必须恰好等于固定提交 + 系列）、
    `verify-upstream.py --series-only`（只核对锁里的系列本身，发布工作流用它）；
  - `export-patches.py`：从上游检出的补丁分支稳定导出（diff 与 Git 配置选项全部固定），先在临时目录生成并校验（重放得到的树必须等于分支树、结果过 `load_series`），
    再原子替换，先写新文件、最后才删多余的旧补丁；`impacto_common.py` 放共享的加载与报告代码；
  - `dev-build.sh`：WSL 增量构建，产物 `dev-candidate`，不得发布，Gradle 需 `-PimpactoDevCandidate=true` 才接受，版本名带 `-dev`，且与发布签名密钥互斥；
    构建锁记录 `pid + 进程启动时间`，持有者已退出（或 pid 被别的进程复用）时自动清掉陈旧的锁；CMake 配置与锁解析与发布配方共用 `build-tools.sh` 里的同一份实现；
  - `mo6tw-pc/`：生成 `profiles/mo6tw-pc` 数据的脚本（HUD 坐标按 1.5 倍缩放、由字体图集量字宽等），只含代码，读使用者自己的游戏文件，见其 README。
- `.gitattributes` 对 `engine/impacto/patches/**` 关闭换行转换，补丁字节永不被规范化。
- 已知近似与缺口：标题、存档、选项、附加内容等非对话菜单的坐标由 PS3 配置按 1.5 倍缩放得到，只是近似（文件带 `TODO(tyn)` 头）；`mo6tw-pc` 的存档系统是 TYN 自己的格式（不读 Steam 版存档）；
  附加内容菜单用占位图集；主 Tyranor Next 应用尚不识别 PC 版目录布局（`game.exe` + `data/*.cpk`），目前只能由外部 Intent 指定 profile。
- 存档代码独立审查发现的问题已修复：存档菜单翻页不再在按钮回调里释放正在处理点击的控件组；存档文件任务串行化（后到的排队，写入前在主线程拍快照，工作线程不再读写活的存档状态）；
  快速存档的持久化在有任务运行时排队而不是被丢弃；系统数据先整段解析校验、通过后才应用；Load 模式点空槽不再把确认键交给脚本；存档路径按 UTF-8 构造（Windows 下用宽字符 API 写入）；
  删除已无使用者的 `SaveData.AllowMissingImplementation`。真机（荣耀 PPG-AN00，Android 17，`mo6tw-pc-zhs`）复测：约 34 次 PREV/NEXT 连点无崩溃；存档→强制停止→重启→读档回到同一幕同一句；
  快速存档连点后 `SYSTEM.DAT` 的 CRC 与结构完好、无残留临时文件，且槽位数与内存一致。**未验证**：Windows 构建与非 ASCII 路径、损坏系统数据的行为只做了代码审查、其他游戏没有设备回归。
- NOTICE：APK 含经修改的 ISC 上游源码，修改即补丁系列；发布的许可证文本包同时附带补丁系列；补丁系列自身的许可证待仓库所有者确定（NOTICE 里有占位说明）。
- 发行版与宿主 APK 改用新名字「Tyranor Next MAGES」：发布标题为「Tyranor Next MAGES <版本>」，发布资产改为 `Tyranor-Next-MAGES.apk`、`Tyranor-Next-MAGES.sha256`、`Tyranor-Next-MAGES.candidate.json`、`Tyranor-Next-MAGES.licenses.tar.xz`（资产名不能含空格，用连字符），宿主应用名由「MAGES.（impacto）」改为「Tyranor Next MAGES」。标签仍是 `impacto-host-<版本>`，包名与 Intent 协议不变。
- 0.2.0 另附一份与 `Tyranor-Next-MAGES.apk` 逐字节相同的 `impacto-host.apk`，只为让写死旧资产名的旧版 Tyranor Next 继续能从 `releases/latest/download/impacto-host.apk` 下载。**这份兼容副本只在 0.2.0 里有，之后的版本不再附带**：旧版 Tyranor Next 的旧链接会从下一个发布起失效，Tyranor Next 的下载链接需要改为 `Tyranor-Next-MAGES.apk`。0.1.2 及更早的发布仍带 `impacto-host.*` 资产，不会被改动。

## 0.1.2（versionCode 3）

- 支持接收 Tyranor Next 的引擎设置（0.1.2）。
- 宿主 0.1.2（versionCode 3）：新增 `SETTINGS` extra，Tyranor Next 的 MAGES. 引擎设置经它合并进该游戏的 `userconfig.toml`（`ImpactoSettings` 严格解析、`ImpactoUserConfig` 按行合并，只改受管键；字幕轨写成引擎的标志格式 `"Karaoke|Translation"`，不认识的文件布局先备份再重建，原子替换，游戏进程在跑时不改文件）。

## 0.1.1 及更早

- 本仓库由 Tyranor Next 的 MAGES. 引擎（impacto 项目）集成拆出，作为宿主 APK 的长期维护与下载位置。
- 引擎名统一为 MAGES.；impacto 是项目名。宿主应用名改为「MAGES.（impacto）」，发布标题与说明同步（0.1.1）。
- 宿主 APK 没有桌面入口：只有一个供 Tyranor Next 调用的导出 Activity，不带 `MAIN`/`LAUNCHER`。
- 上游库用 NDK `27.3.13750724` 构建（`source-lock.json`），打包时显式 `llvm-strip` 并核对 GNU build-id，避免 APK 膨胀到 400 MB 以上。
- 发布工作流产出固定名称的资产（`impacto-host.apk`、`impacto-host.sha256`、`impacto-host.candidate.json`、`impacto-host.licenses.tar.xz`），并标为最新正式版，Tyranor Next 直接下载 `releases/latest/download/impacto-host.apk`。
