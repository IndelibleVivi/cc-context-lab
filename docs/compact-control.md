# Compact 自定义控制面

核对日期：2026-10-05（Asia/Singapore）。本文以官方文档与 types 研究 compact；后续本地命令探针已生成目标 **2.1.289** types，并补读下表所列 compact symbols。**没有**执行 compact、安装 profile、发真实模型请求或抓取 request body。按层的其他官方入口见 [official controls](official-controls.md)；compact 之后的重载、恢复与语义连续性见 [continuity and memory](continuity-and-memory.md)。

## 四层证据必须分开

compact 的一切结论都受“读的是哪一层”限制。本文区分四层，并逐条标注依据：

| 层 | 本次读到的对象 | 能支持什么 | 不能支持什么 |
| --- | --- | --- | --- |
| 官方文档 | `code.claude.com` 各页 `.md` 正文，reference 以 **v2.1.289** 为描述基线 | 官方承诺的入口、行为描述、版本注记 | 目标安装是否照此执行 |
| 公开 types | exact revision [`2bfb629d`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts) 的 `mods/types/claude-code.d.ts` | 事件/字段的静态形状与注释承诺 | 运行时会命中哪些事件、handler 是否加载 |
| 目标生成 types | 本地命令探针生成 **2.1.289**，已补读 compact input/result/trigger、messages/handle（见 [target runtime](target-runtime.md)） | 目标版本的字段与注释合同 | compact 实际执行、摘要质量与全部内部模板 |
| 真实 compact runtime | 未观察。无 request body、无截断/重载实测 | 最终 request、磁盘 transcript、行为 | —— |

**版本分歧**：官方 Mods reference 现标 v2.1.289，而公开 types 首行仍写 `Written by Claude Code 2.1.277.`。本次还比对了本机另一份已读公开 types（同源 `claude-code.d.ts`）：两份 header 都为 2.1.277，且本轮对照的 compact 相关 symbol **无差异**。这一历史对照只能说明两份公开类型面一致。后续已用独立本地命令生成 2.1.289 目标声明，确认 compact 的 inputs、完整 messages/skip 输出与 handle 合同仍存在；不是靠两份旧文件推断。本文只读 compact 相关 symbol，不做全 repo 审计；应以目标 build 为 mod 目录生成的 types 为准，见 [Get type definitions for your version](https://code.claude.com/docs/en/plugins/mods/create#get-type-definitions-for-your-version)。该入口随目录加载生成文件；旧记录中的 `/plugin-types` 并非已核实的命令。

## 入口一：`/compact [instructions]` 与 CLAUDE.md 的 Compact Instructions

文档层事实：

- [`/compact [instructions]`](https://code.claude.com/docs/en/commands#all-commands)：摘要当前对话以释放 context，可传 focus instructions；例 `focus on the auth bug fix`。见 [Compact with a focus](https://code.claude.com/docs/en/context-window#when-your-context-fills-up)。
- [The context window](https://code.claude.com/docs/en/how-claude-code-works#the-context-window)：可以在 CLAUDE.md 添加 **Compact Instructions** 小节，持续指导压缩保留内容。

区分两点：

1. **CLAUDE.md 写 "Compact Instructions" 小节是文档支持的用法**，不是“不支持”。公开 types 无对应 typed 字段，只说明**它是否被内部拼装成 `session.compact` 的 `instructions`、还是靠 CLAUDE.md 本身重载生效，尚未验证**。
2. `/compact` focus 与事件 `instructions` 有直接关联：`SessionCompactArgs.instructions` 注释明确指向 `/compact` 后输入的保留重点（[types L8592-8600](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8592-L8600)）。CLAUDE.md 小节走哪条路则未证。

`/compact` 是 built-in 命令，不是 Skill：[skills.md](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill) 说明 `/compact` 一类 built-in 命令不经 Skill 工具暴露给模型。

## 入口二：`session.compact` mods 事件与 `$.session.compact`

types 里 compact 事件与调用（均取同一 exact revision；链接给出 blob 行锚）：

| symbol | 形状 | 关键承诺 |
| --- | --- | --- |
| [`SessionCompactTrigger`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8692-L8694) | `'manual' \| 'auto' \| 'plugin' \| 'precompute'` | 谁在压 |
| [`SessionCompactInput`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8631-L8663) | `{ trigger, agentId?, instructions?, messages }` | `next({ ...e, instructions })` 改摘要被交代什么；`next({ ...e, messages })` 改被摘要内容；`trigger`/`agentId` pinned，改写会失败 |
| [`SessionCompactArgs`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8595-L8601) | `{ instructions?: string }` | **插件主动调用** `$.session.compact(args)` 只能传 instructions |
| [`SessionCompacted`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8607-L8629) | `{ messages, tokensBefore?, tokensAfter?, skip?: undefined }` | 压缩后的对话，oldest first；摘要本身是一条 message，没有独立 summary 字符串 |
| [`SessionCompactSkipped`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8674-L8685) | `{ skip: string, messages?: undefined }` | veto |
| [`SessionMessage`](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8964-L8988) | `{ role, text, toolUses, toolResults?, handle? }` | `handle` 是 engine 给“它自己的消息”盖的 opaque token |

### 事件返回能自写“完整 messages”

`SessionCompacted.messages` 允许 hook 返回自己构造的整条消息列表，不只是 `{ skip }` 或改 instructions。types 注释明确接受 hook 交回的消息列表，并区分 engine 原消息和由字段重建的消息。（[L8611-8623](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8611-L8623)）

两种语义：带 `handle` 的消息 = engine 自己的、完整的；无 `handle` 的按 `role/text/tool blocks` 重建。`handle` 只在 engine 把列表交给 `session.compact` hook 时盖上，`$.session.messages()` 上**没有**（[L8983-8987](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8983-L8987)）；要留成 engine 原件，必须用 engine 递下来的那份对象。

**直接返回 messages 是一条独立的控制路径**：它绕过（替代）该事件下游的 engine 摘要步骤——不是“喂料 + 收结果”，而是由 hook 直接决定这份压缩后 transcript 长什么样。后续是否还有其它重载路径，范围未验证。

### `$.session.compact()` 的调用条件

types 注释（[L2449-2459](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L2449-L2459)、[L3900](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L3900)）与[事件声明 L3565-3575](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L3565-L3575)：

- 触发 `session.compact` 事件，`trigger='plugin'`，与 `/compact` 同一调用，**between turns**。
- 调用方自己的 hook 被跳过，其余 hook 链继续处理，默认终点是 core。
- 有 hook veto 时解析为 `{ skip }`。
- **`rejects while a turn runs`**：turn 进行中调用会被拒绝。
- 签名 `compact: (input?: SessionCompactArgs) => Promise<SessionCompactResult>`：参数可选。

用明确 types 形状表示 hook 的三种返回（`SessionCompactResult = SessionCompacted | SessionCompactSkipped`）：

```ts
next({ ...e, instructions: 'keep the plan' })   // 只改摘要指令 -> Promise<SessionCompactResult>
next({ ...e, messages: myMessages })            // 改被摘要内容 -> Promise<SessionCompactResult>
{ messages: myMessages }                        // 直接替换压缩后 messages -> SessionCompacted
{ skip: 'reason' }                              // veto -> SessionCompactSkipped
```

（示意为 types 形状，不执行、不安装 plugin；未运行 compact handler。）

### subagent / loop 边界

`SessionCompactInput.agentId` 注释（[L8639-8648](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8639-L8648)）：`agentId` 是**正在 compact 的 loop**（subagent 或 fork 自己的 transcript），主对话时缺席，取值同 `tool.call`，且 pinned（改写省略会被补回，改了失败）；**`$.session.messages()` 无论 `agentId` 为何，返回的都是主对话**，子代理 transcript 在其 `agentId` 下另给。即主线程与 subagent/fork 是**不同 loop**，hook 只处理主路径不能推定子路径也被处理。

### trigger 语义

- `manual`：用户 `/compact`。`auto`：engine 在阈值或 prompt 过长时。`plugin`：`$.session.compact()` 发起。`precompute`：注释规定此时结果不安装到当前对话，而是为后续压缩保留（[L8691-8694](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L8691-L8694)）——即不安装，结果被缓存给随后的 compact，**条件是它跑过的那段对话仍是对话前缀**。文档没有单列 precompute，本文不对其原因作推测。

## PreCompact / PostCompact / SessionStart 的能力

两层 API 并存：**classic hooks**（settings hooks，JSON in/out）与 **mods events**。本文按公开 types 与 [Hooks reference](https://code.claude.com/docs/en/hooks) 描述。classic 事件亦见 `HookInput`（[L4288](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L4288)）。

### PreCompact

- types（[L6385-6390](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L6385-L6390)）：`{ hook_event_name: 'PreCompact', trigger: 'manual' | 'auto', custom_instructions: string | null }`。
- 文档（[PreCompact](https://code.claude.com/docs/en/hooks#precompact)）：`trigger` 为 `manual`/`auto`；`custom_instructions` 在 manual 时是用户传入 `/compact` 的文本、未传为 `null`，auto 时为 `null`。
- 能力：**exit code 2 或 `{"decision":"block"}` 可 block compaction**。blocking auto 分两种：接近阈值时提前触发的压缩被跳过、对话保持未压缩；若是在 API 已返回 context-limit 错误后的恢复压缩，则底层错误上浮、当前请求失败。
- 限制：PreCompact hook 的 `systemMessage` 与 `continue` 被丢弃；`ClassicResultFields`（[L1063](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L1063)）里没有 `PreCompact` 条目。
- classic trigger 只有 `manual|auto`，**没有显式给出 partial mapping**——这不证明局部 summarize 不经过 `session.compact`，只说明公开文档/类型未把它列在该处。

### PostCompact

- types（[L6296-6302](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L6296-L6302)）：`{ hook_event_name: 'PostCompact', trigger: 'manual' | 'auto', compact_summary: string }`。
- 文档（[PostCompact](https://code.claude.com/docs/en/hooks#postcompact)）：**无决策控制**，不能影响 compression 结果，只能做后续动作；`systemMessage`/`continue` 同样被丢弃。

**证据差别**：classic `PostCompact` 能拿到摘要字符串 `compact_summary`；mods `SessionCompacted` **没有 summary string**，摘要是一条 message。两种接口形状不同；自定义 messages 后 classic hook 实际看到的内容尚未验证。

### SessionStart

- types（[L9153-9173](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L9153-L9173)）：`source: 'startup' | 'resume' | 'clear' | 'compact' | 'fork'`。
- 文档（[SessionStart](https://code.claude.com/docs/en/hooks#sessionstart)）：`source='compact'` 表示 compaction 之后；[What survives compaction](https://code.claude.com/docs/en/context-window#what-survives-compaction) 明确匹配该 source 的 hooks 会重新运行，输出进入压缩后的 context。
- 能力（`ClassicResultFields.SessionStart`，[L1063](https://github.com/anthropics/claude-code/blob/2bfb629dfaff0c8318047a4beb93cf1dc5b58b18/mods/types/claude-code.d.ts#L1063)）：`additionalContext`、`initialUserMessage`、`sessionTitle`、`watchPaths`、`reloadSkills`。**这是 compact 后重新注入自有 context 的公开通路**。
- 边界：`sessionTitle` 在 `clear` 与 `compact` 时被忽略；`reloadSkills` 让 CC 在 SessionStart hooks 完成后重扫 skill/command 目录。首个请求的 SessionStart 与 `Setup` 在 MCP server 可用之前 fire，其 `mcp_tool` hooks 会被跳过；`/clear` 或 compaction 后再 fire 时才有 MCP 上下文。

即 **PreCompact/PostCompact 是 classic hooks 的观察/阻断接口，mods 侧对应 `session.compact`；compact 后的重载主要走 SessionStart(`compact`) + engine 自身重载**，而非 PostCompact（后者无 context 决策能力）。

## 局部 summarize / checkpointing

与整体 compact 分开的路径（[Checkpointing](https://code.claude.com/docs/en/checkpointing)、[Rewind and summarize](https://code.claude.com/docs/en/checkpointing#rewind-and-summarize)）：

- `/rewind`（或空输入下双 `Esc`）打开 rewind 菜单；每个“开始一个 turn 的 prompt”创建一个 checkpoint，保留最近 100 个文件快照，与 conversation 一起保存，`--resume` 后仍可用。
- **Summarize from here** 压缩该点之后的对话；**Summarize up to here** 压缩该点之前、保留其后消息。
- “Guide a summary”：高亮 Summarize 选项后在 `add context (optional)` 行输入 instructions。
- Note：Summarize 在同一 session 内压缩 context，“like a targeted `/compact`”。

需要区分的两点：

1. 文档只说局部 summarize “像” 定向 `/compact`，**没有**说它触发 `session.compact`，也未给出 trigger 值。因此“局部 summarize 是否经过 `session.compact`、能否被自定义”**未验证**——未验证 ≠ 已证明不经过。
2. 文档说 Summarize “doesn't change files on disk, and the original messages stay in the session transcript”：这里“不改文件”指**不回滚工作区文件**（对比 restore code），且**原历史保留**。这不等于 runtime 不写任何存储；transcript 与压缩标记的具体落盘细节未核。

## 自定义 skill 与内置 compact 的关系

- 命令面：`/compact` 是 built-in 命令，不是 Skill，不经 Skill 工具暴露。
- 内容面：已调用 skill 正文按下方预算重挂并被截断（[Skill content lifecycle](https://code.claude.com/docs/en/skills#skill-content-lifecycle)）。
- 清单面：skill listing（描述清单）**不**在 compact 后重注入，保留范围是已经调用过的 skills（[context-window](https://code.claude.com/docs/en/context-window)）。

## 压缩后哪些来源重载、哪些技能截断

以下是相应来源启用时的文档行为；禁用来源或自有 Mods 的后续变换需要另验。依据 [What survives compaction](https://code.claude.com/docs/en/context-window#what-survives-compaction)：

| 机制 | compact 之后 |
| --- | --- |
| System prompt 与 output style | 继续生效 |
| 项目根 CLAUDE.md 与 unscoped rules、Auto memory、plan mode 的 plan | 从磁盘重注入 |
| Git status snapshot | 从 repo 重读一份新的 |
| 带 `paths:` frontmatter 的 rules / 子目录 nested CLAUDE.md | 在 Claude 读到匹配文件时重载 |
| Claude 读过/改过的文件 | **最多重读 5 个，最近修改优先**；单文件 > 5,000 tokens 退化为 path reference（`Referenced file`，无内容） |
| 已调用 skill 正文 | 重注入，**每 skill 上限 5,000 tokens、总计 25,000**，最旧的先丢（保留文件开头） |
| 后台 commands / background subagents | 继续运行；CC 提醒模型哪些仍在跑，避免重复启动 |
| **更早由 hooks 加入的 context** | **随其余对话一起被摘要**（不保证重注入） |
| match `compact` 的 SessionStart hooks | CC 运行它们并把输出加入压缩后的 context |

要点：engine 自己的 startup reminder（CLAUDE.md、git snapshot、plan、auto memory 等）会重新生成；**之前由 hooks 注入的 context 会参与摘要，原文不保证保留**；需要原文时可设 match `compact` 的 SessionStart hook 重新提供（subagent 场景亦见 [hooks](https://code.claude.com/docs/en/hooks)）。这与 [continuity and memory](continuity-and-memory.md) 中“清理默认 reminders 时保留自有 hook context 通路”一致。另：自 v2.1.198 起摘要请求继承 session 的 extended thinking 配置，但那只影响**摘要如何产生**，不改 session 设置。

## “能改摘要” vs “已覆盖所有 utility prompts”的证据差别

| 主张 | 现有证据 | 判定 |
| --- | --- | --- |
| 能改发给 summarizer 的 instructions | `SessionCompactInput.instructions` + `next({ ...e, instructions })`；`SessionCompactArgs.instructions`；types 注释把它与 `/compact` focus 关联 | **文档 + 公开 types 支持** |
| 能改被摘要的 messages | `next({ ...e, messages })` | **文档 + 公开 types 支持** |
| 能直接返回自写完整 messages | `SessionCompacted.messages`；无 handle 者按 role/text/tool blocks 重建 | **公开 types 支持**；无 runtime 证据 |
| CLAUDE.md 的 Compact Instructions 小节被支持 | [how-claude-code-works](https://code.claude.com/docs/en/how-claude-code-works#the-context-window) 明确支持该用法 | **文档支持**；是否内部映射成 `instructions` **未验证** |
| 已覆盖 engine 的全部内部摘要模板 / utility prompts | 无可读字段或文档承诺说明每个内部模板被暴露 | **未证**（不是“已证明不覆盖”）；后续事件可能另有路径，范围未验证 |

对命中此事件的路径，可以修改默认流程的输入/结果，也可以直接返回 messages 来替代下游流程。是否覆盖其他内部摘要路径仍需取证，见 [current state](current-state.md) 第 3 条。

## 阅读覆盖

本次实际读过：

- `mods/types/claude-code.d.ts`（exact revision `2bfb629d`）：`SessionCompactTrigger/SessionCompactArgs/SessionCompacted/SessionCompactInput/SessionCompactResult/SessionCompactSkipped`、`SessionMessage`、`$ .session.compact` 与 `usage`、`EventCalls.session.compact`、事件声明与结果映射、`Pre/PostCompactHookInput`、`SessionStartHookInput`、`ClassicResultFields`、`PromptAttachmentInput`。**未做全 repo 审计。**
- 官方文档（仅本文相关小节，非各页全文）：[commands](https://code.claude.com/docs/en/commands)、[context-window](https://code.claude.com/docs/en/context-window)、[how-claude-code-works](https://code.claude.com/docs/en/how-claude-code-works)、[memory](https://code.claude.com/docs/en/memory)、[skills](https://code.claude.com/docs/en/skills)、[hooks](https://code.claude.com/docs/en/hooks)、[checkpointing](https://code.claude.com/docs/en/checkpointing)、[plugins/mods/reference](https://code.claude.com/docs/en/plugins/mods/reference)、[plugins/mods/test](https://code.claude.com/docs/en/plugins/mods/test)。
- 本轮未补读 2.1.288/2.1.289 changelog；env-vars、cli-reference、monitoring-usage、agents-md 沿用先前专题证据，没有以本轮日期重新认证。

## 待验证项

目标 2.1.289 的上述 compact 字段已补读（并非声明全文 diff）；仍需隔离 compact runtime 取证（**未执行**）：CLAUDE.md Compact Instructions 小节是否拼进 `instructions`；局部 summarize 是否经 `session.compact` 及其 trigger；`precompute` 缓存“仍是对话前缀”的真实失效条件；`handle` 保真；主/子 loop 的 `agentId` 行为；compact 后 request 的实际重载与截断；`session.compact` 是否覆盖全部内部摘要模板（**当前未证**）。

本文不声称 compact 已实测或生产支持；不复制官方长篇正文，只引用必要短例与字段。相关官方控制面见 [official controls](official-controls.md)，compact 之后的连续性与 Memory 见 [continuity and memory](continuity-and-memory.md)。
