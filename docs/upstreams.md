# 上游机制对照

Forge / Swap / Carryover 的新专题见 [Forge upstreams](forge-upstreams.md)；Pi 原生投影、Cliff proxy、Claude 服务端机制的有界对照见 [continuity and memory](continuity-and-memory.md)。它们补充上下文生命周期研究，不替代下列默认提示与 reminder 的逐项分析。

核对：2026-10-03。七个公开仓库按 default branch exact commit 拉取后做有界 source 阅读；另外对已读 roof handler 运行了六项合成复现及两项对照，见 [experiment record](../experiments/README.md)。还对 fixed 的选定原函数做了五组合成 placeholder/apply 检查；没有安装依赖、运行文件系统 apply driver、加载真实 CC mod 或发模型请求。完整 revision 与已读路径在 [catalog](../references/upstreams.json)。README 的支持范围与统计属于作者声明。

## 先看机制

| 项目 | 对我们有用的责任 | 当前采用判断 |
| --- | --- | --- |
| roof-mod | Mods 事件入口、只读探针、局部改写样例 | 研究结构入口；不直接采用默认静音和全局字串改写 |
| lobotomized-claude-code | 已做内容判断的 overrides 包 | 对照每项保留/删除的意图；不整体照搬作者偏好 |
| tweakcc-fixed | reminder registry、占位符处理、应用流程 | 深读候选，先拆清非提示副作用和目标版本支持 |
| tweakcc | 通用 prompt 管理与 patch 工具 | 与 fixed 比较具体源码，不能按名字推断能力 |
| claude-code-custom-prompt | core 拼装与版本绑定 patch 方法 | 保留旧方法的价值，更新 snapshot 与平台假设 |
| claude-code-system-prompts | 静态提示目录与版本变化 | 定位要研究的片段；不能证明某次真实运行使用了它 |
| cchistory | 从实际请求生成对照结果 | 观察方案参考；执行包含模型请求，当前未运行 |

## roof-mod：接口有用，改写边界需要重做

[roof-mod/hooks/register.js](https://github.com/kagamiurayama/claude-code-roof-mod/blob/888dceb88631186dfcf01d69b088bedec9c1009a/roof-mod/hooks/register.js) · [probe-mod/hooks/register.js](https://github.com/kagamiurayama/claude-code-roof-mod/blob/888dceb88631186dfcf01d69b088bedec9c1009a/probe-mod/hooks/register.js) · [tools/gen_fragments.py](https://github.com/kagamiurayama/claude-code-roof-mod/blob/888dceb88631186dfcf01d69b088bedec9c1009a/tools/gen_fragments.py)

该 revision 注册 `prompt.attachment`、`prompt.context`、`prompt.compose`。默认 `FRAGMENTS` 为空，静音/开场白与身份改写仍会运行。生成器读取可执行文件并围绕 `edited_text_file` 锚点提取文本，外加手工短语；不修改 binary 不等于不依赖 binary 布局。

handler 存在明确的作用域问题：静音判断先于 origin 检查；`rewriteInstructions` 对整个字符串删除 preamble；channel guard 只约束 `rewriteProse`。这些行为均在原 handler + 合成输入下复现。新增 F01 还复现了插件 section 内的身份句引用被全局改写；F05a/b 显示静音会丢弃合成动态事实。因此注释的“夹带原文不动”不能仅靠匹配固定短语保证。未验证真实 CC 是否发出每种构造事件。

探针记录 attachment 的输入发生在 `next(e)` 之前；section / compose 则在之后读结果。探针适合发现事件，不能统一标为最终 request。README 的加载签到是教程示例，不在已读成品 handler 中。覆盖到这里，不声称阅读了 PDF 或运行过 Mods tests。

## lobotomized：把内容取舍变成逐份文件

[README.md](https://github.com/skrabe/lobotomized-claude-code/blob/053d8703592ab7211fdf2374006d108e42f6decc/README.md) · [system-reminders/task-list-reminder.md](https://github.com/skrabe/lobotomized-claude-code/blob/053d8703592ab7211fdf2374006d108e42f6decc/system-reminders/task-list-reminder.md) · [system-reminders/mcp-per-server-router.md](https://github.com/skrabe/lobotomized-claude-code/blob/053d8703592ab7211fdf2374006d108e42f6decc/system-reminders/mcp-per-server-router.md)

当前目录使用一套 `system-prompts-lcc/` 和 `system-reminders/`。本轮已逐份检查全部 41 个 reminder 文件，含 34 个内容条目、1 个 router marker、6 个 per-server 文件。task-list、hook additional-context、nested-memory 分别保留动态任务、hook 原文、memory path/content；其他文件的保留/删除选择与 apply 路径见 [逐项表](reminder-overrides.md)。

一个重要例外：MCP routing marker 的空正文表示关闭自定义路由、回到 pristine server instructions；不是把所有 MCP instructions 删除。不能将“空文件就是静默”扩展成每个文件的统一合同。

作者的模型行为判断与 token 统计未复测。reminder 文件的有界审阅已完成；`system-prompts-lcc/` 的组成已做确定性文件/正文对应，见下与 [Prompt differences](prompt-differences.md)。 旧 pin 的该目录有 9,491 个 `.md`；10/05 读到的 tip `b867bb28`（作者标 CC 2.1.288）有 9,771 个，其中 system-prompt 645、tool-description 818、tool-result 4,389、agent-prompt 347、system-reminder 533。把文件名当作 pristine id、正文（header 移除并 strip 后）对**同版本** `prompts-2.1.288.json`（作者自带 extractor 产出）比较后：exact 3,598、norm_only 5,128、changed 805、suppressed 202、unmatched 38（全是作者拆分的 `inline-*`）；可对应 9,733。**文件数不是改写数**；exact 指 body 相同（非原始文件逐字节），`norm_only` 不等于作者未改；作者 README 的 764 rewritten + 199 cut 是 2.1.280 口径的作者报告。changed 内的实质改写与 38 个 unmatched 仍未逐份语义深读。复现见 [compare_prompt_inventory.py](../scripts/compare_prompt_inventory.py)；四 repo 增量与读到的 2.1.288 变化见 [Prompt differences](prompt-differences.md)。

## tweakcc-fixed：覆盖 reminder，但 apply 还会改行为

[src/systemReminderSync.ts](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/systemReminderSync.ts) · [src/patches/systemReminderOverrides.ts](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/patches/systemReminderOverrides.ts) · [src/patches/index.ts](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/patches/index.ts)

`systemReminderSync.ts` 解析 HTML-comment frontmatter，保存 `ccVersion` / placeholders，正文为空时得到 `isSuppressed`；插值前检查白名单，普通正文经反斜线、反引号、插值起始与 non-ASCII 转义。具体效果还取决于 registry 的 apply 实现，不能只看解析器。

`systemReminderOverrides.ts` 的 registry 涵盖 CLAUDE.md、skills、MCP、hooks、工具结果、nested memory、任务等注入点，并有 MCP per-server router。大量匹配针对 minified code shape；升级后必须重新证明目标位置及变量语义。本轮把 35 个 registry 条目的 apply 路径逐项对应到 reminder 清单，补读 shadow 扫描；placeholder 链路有五组合成检查，其他安装/恢复行为仍未运行。

`src/patches/index.ts` 中摘要起点和 rewind header 修正在配置不为 false 时启用；还有 always-applied 空 reminder wrapper、Read 默认行数入口等。全局 cache scope 也有身份行替换相关处理。运行 `--apply` 不能先假定“只应用了自己的 Markdown”。这些是源码控制分支，不是本机应用结果。

## tweakcc upstream：修正 fork 文档的一条过时比较

[src/patches/index.ts](https://github.com/Piebald-AI/tweakcc/blob/d839e046ff8036763ddaea42197e9dc88be65b33/src/patches/index.ts) · [src/patches/systemPrompts.ts](https://github.com/Piebald-AI/tweakcc/blob/d839e046ff8036763ddaea42197e9dc88be65b33/src/patches/systemPrompts.ts)

**本次 upstream revision 的 apply 流程已经在 native 解包后调用 `applySystemPrompts`，并包含 native repack 路径。** fixed README / 源码注释中“upstream skips native”的宽泛表述不符合这份已读 upstream revision。不能再用它作为选择 fork 的充分理由。

这不等于两者覆盖一致：具体 prompt、模块、reminder registry、版本和安装格式仍要比较；部分 prompt 本身可能有独立跳过条件。通用工具还提供 restore、unpack/repack、冲突处理与自定义 patch 的入口（README）。本轮未测试任何安装、恢复或升级过程。

## custom-prompt：旧方法有价值，wrapper 仍是示例

[README.md](https://github.com/rossignol6712/claude-code-custom-prompt/blob/cc05da770f0a9480b38cff56cc3ab88623bd3453/README.md) · [examples/scripts/cc-wrapper.sh](https://github.com/rossignol6712/claude-code-custom-prompt/blob/cc05da770f0a9480b38cff56cc3ab88623bd3453/examples/scripts/cc-wrapper.sh)

wrapper 按编号拼接 Markdown，有 persona 追加路径；没有编号块时退回 append-only。它仅在参数等于 `--system-prompt` / `--system-prompt-file` 时识别显式 override，因此不能把“尊重调用方所有等价参数写法”当成已证合同。

示例还硬编码 environment 的 Linux/bash 文案，并用按 model 命名的临时文件。它适合作为拼装方式参考，不宜未经修改当跨平台或并发 launcher。

README 的 compact 部分描述 2.1.207 的三个摘要模板及定位/验证方法；当前目录没有交付那套独立完整 patch 程序。旧版结论与当前 Mods 能力需要重新对应，不能从方法文档推断已有安装包。

## 静态目录与运行 trace 是两种证据

[README.md](https://github.com/Piebald-AI/claude-code-system-prompts/blob/e6184590031d8d194074130b5e3eef7b4bbd2055/README.md)

system-prompts README 覆盖 system sections、tools、agent、utility/compaction 等，当前版本标 2.1.287。目录证明有这些候选片段，具体运行仍受配置、模式与条件分支影响；本轮仅读范围说明与目录入口，没有全文复制或声称逐份验证。

[README.md](https://github.com/badlogic/cchistory/blob/cdf2f25b54bcec005acd37fc191594607d66694f/README.md) · [src/index.ts](https://github.com/badlogic/cchistory/blob/cdf2f25b54bcec005acd37fc191594607d66694f/src/index.ts)

cchistory 的 `src/index.ts` 确实通过 `claude-trace` 启动 CC 并发送测试 prompt；它不是纯离线 extractor。README 还说明输出不含 MCP tools。其 snapshot 的 commit 日期为 2025-10-30，不能默认宣称兼容本次研究的 2026 年 Mods/build。优先比较官方 raw-body logging 是否已能满足当前观察需要，再决定是否采用额外 trace 工具。

## 下一项最有价值的研究

reminder 内容目的、运行事实与 fixed 应用点已进入 [逐项表](reminder-overrides.md)，官方接口与缺口进入 [迁移表](mods-migration.md)。接下来对 named system prompts 与 tool descriptions 做同样深度的核对，再设计完整 profile；当前没有依据宣布所有 binary patch 已过时，也不直接接受整套 fork 的附带行为。
