# 补丁系列

本目录是叠在**固定的上游 impacto 提交**（`../source-lock.json` 的 `impacto.revision`）之上的、经审计的补丁系列。
构建出的 `libimpacto.so`、打包进 APK 的 Java 层与资源（`profiles/`、`resources/`、着色器、`gamedefinitions.lua`），
都来自「固定提交 + 本系列」，不含其他改动。

| 文件 | 作用 |
| --- | --- |
| `NNNN-short-name.patch` | `git format-patch` 格式的补丁，四位序号递增，一个补丁一类改动 |
| `series` | 按顺序列出补丁文件名，每行一个；空行与 `#` 开头的行是注释 |
| `../source-lock.json` 的 `patches` | 完整性记录：`directory`（相对 `source-lock.json`）与有序的 `series: [{file, sha256}]` |

补丁文件、`series` 与 `source-lock.json` 三者必须一致：文件缺失、多出未登记的 `*.patch`、顺序不同、SHA-256 不符，
`verify-upstream.py --patched`、`verify-upstream.py --series-only`、`apply-patches.py`、构建与 Gradle 都会直接失败。
**不要手改这些文件**（`.gitattributes` 也对本目录关闭了换行转换，补丁字节永不被规范化），用下面的流程生成。

## 维护流程

补丁以提交的形式维护在一份上游 checkout 的分支上，再用脚本导出。

```sh
# 1. 取一份上游检出，建分支，位置必须在固定提交之上
git clone https://github.com/CommitteeOfZero/impacto.git ~/impacto-patches
cd ~/impacto-patches
git checkout -b tyn <source-lock.json 里的 impacto.revision>

# 2. 一个提交 = 一个补丁。提交标题用 ASCII 描述，会成为文件名（0001-<标题>.patch）；新增文件要先 add
git add -A && git commit -m "tyn: add mo6tw-pc profile"

# 3. 导出：重写本目录的补丁与 series，并更新 source-lock.json 里的 sha256
python tools/impacto/export-patches.py --source ~/impacto-patches --branch tyn
```

### 提交的分组约定

- 一个提交只做一类改动，标题以 `tyn: ` 开头加 ASCII 描述（它就是补丁文件名与审计时看到的标题）。
- 通用的引擎修复（对上游其他 profile 也成立、可以直接向上游提 PR 的）与 TYN 专有内容（`mo6tw-pc*` 的 profile、`gamedefinitions.lua` 注册等）**分成不同的提交**，
  并在提交正文里写明「可向上游提交」或「仅 TYN」，方便以后挑出来提 PR、或在上游吸收后直接丢掉。
- 补丁之间按依赖排序：先通用修复与 profile 开关，再指令集，最后 profile 数据与注册。

### 导出的保证

导出脚本要求分支是线性的（没有合并提交）且以固定提交为起点；它用稳定的 `git format-patch` 选项
（无版本签名、提交号清零、完整索引行、不做重命名检测，diff 上下文与 `diff.*`／`core.quotepath` 等 Git 配置也都固定），
未改动的提交每次导出字节一致，diff 里只有真正改了的补丁。
导出先在临时目录生成并校验：在固定提交上重放整个系列，结果的树必须与分支末端的树完全相同，暂存出的结果还要通过构建同一套 `load_series` 检查；
任何一步失败都不写入仓库。通过后才原子替换（先写新补丁与 `series`，再换 `source-lock.json`，最后删掉不再在系列里的旧补丁）。

提交前自检（需要一份**干净的**固定提交检出，例如 `git clone` 后 `git checkout <revision>`）：

```sh
python tools/impacto/apply-patches.py --source <干净检出> --report <目录外>/applied.json
python tools/impacto/verify-upstream.py --patched --source <干净检出>
python tools/impacto/test-patch-series.py
```

`apply-patches.py` 只接受「固定提交且完全干净」或「已经恰好是固定提交 + 本系列」的检出，用 `git apply --index`
按顺序应用（不需要提交者身份，不产生提交），其他任何状态都拒绝；重复运行是安全的。

## 同步上游（升级固定提交）

1. 取新的上游提交，把补丁分支变基上去：`git fetch origin && git rebase --onto <新提交> <旧 revision> tyn`，解决冲突；
   上游已吸收的补丁直接丢掉对应提交，确认其余补丁仍然必要。
2. 把 `source-lock.json` 的 `impacto.revision` 改为新提交（导出的基点取自它，所以要在导出之前改）；同时核对 `libatrac9`、`imgui`、`magic_enum`、vcpkg 与 NDK 等其他固定项是否需要随上游更新。
3. 重新导出：`python tools/impacto/export-patches.py --source … --branch tyn`，序号由脚本重排。
4. 在新提交的干净检出上跑上面「提交前自检」的三条命令，再运行 `python tools/impacto/verify-upstream.py --series-only` 与 `python tools/impacto/test-profiles.py --source <补丁后检出>`。
5. 构建：迭代用 `tools/impacto/dev-build.sh`，发布用 `tools/impacto/build-upstream.sh`（新建构建根）。
6. 设备验证（见 `../host-apk/README.md`）：补丁改了引擎行为，编译通过不等于兼容。

## 约束

- 补丁只放 TYN 兼容性所需的最小改动（例如新增 `mo6tw-pc` profile 对应的引擎与 `gamedefinitions.lua` 内容），
  不放构建脚本、依赖版本或无关的重构；上游已有的行为问题先考虑向上游提 PR。
- 补丁文件是 GPL 宿主仓库里的**对 ISC 上游的修改**，随发布一并提供，见 [`NOTICE.md`](../../../NOTICE.md)。
- 补丁不得修改 SDL3 的 Java 层（`org.libsdl.app`）与 SDL 的 JNI 命名空间：候选库检查会拒绝私有命名空间。
