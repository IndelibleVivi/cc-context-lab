# 公开实现对照：companion context input

观察日期：2026-10-05（Asia/Singapore）。本文是**公开 source 检视**，面向持续人–AI companion 互动里的三类机制：
非提示的自主 turn（unprompted autonomous turn）、自动提供的当下 context（present context）、被动记忆召回（passive memory recall）。
**未部署、未安装、未运行、无真实模型/天气服务调用、无本地 runtime 证据；所有引用均为静态 source 检视。**
exact revision 与每个来源实际读取的文件见 [machine catalog](../references/companion-sources.json)。

> 补充：既有 [Heartbeat / channels](heartbeat-and-channels.md) 是**机制对照**（tick / 唤醒 / 交付分层、
> 官方 scheduler / channel 与 OpenClaw 对照）。本文**补充** companion 视角，不重复其细节。

## 先立框架：三类机制不是同一件事

| 机制 | 谁发起 | 目标是「说出去」还是「内部活动」 | 是否必然产生工作任务 |
| --- | --- | --- | --- |
| 非提示的自主 turn | 外部调度/守护进程，或模型自配速 | 二者皆可，必须分开记 | 否；可只记内部状态或静默 |
| 自动提供的当下 context | harness 在 request 装配时 | 内部（进入模型输入） | 否 |
| 被动记忆召回 | 由**机制**在模型前召回并交付正文 | 内部（进入模型输入） | 否 |

三条判据贯穿全文：**（1）静默/内部活动 ≠ 对外消息**（wake 起了 turn、甚至记了时间线，都不蕴含送达）；
**（2）自动注入正文 ≠ 模型自己调用的工具**（hook 在模型前塞正文是 passive，给模型一个「去召回」提示是 model-invoked，
不能把工具提示标成被动召回）；**（3）机制存在 ≠ 已交付**（调度、装配、交付三层各自验收）。

## 来源 1 — Siigari/claude-heartbeat（autonomous turn，Stop→inbox→restart/outbox）

revision [`a561806e`](https://github.com/Siigari/claude-heartbeat/tree/a561806e75fdca540b180df1e541e68d50092bcf)（commit 2026-05-14，GitHub contents API 取得）。
实读：`README.md`、`hooks/heartbeat.js`（140L，全）、`supervisor.js`（170L，全）、`relay/relay.js`（76L，全）、`.claude/settings.json`。未读：`examples/*`、`CLAUDE.md`、`io/*`。

机制链**已在 code 中确认**：`.claude/settings.json` 把 `Stop` 绑到 `node hooks/heartbeat.js`（timeout 30）。每次响应后 Stop hook 触发：
从 `io/inbox.jsonl` 按字节 offset 读**一行**；有消息则 `{decision:'block', reason}`（reason 为 `formatMessage()` 出的 `[time] #channel author: content`）把该行**作为继续输入回注**——
这正是「Stop 即再触发边界」的实现。读完立刻 `writeOffset`（fsync），并写 `.responded` 标记。下一轮 Stop 看到 `.responded`：若 inbox 还有下一条就继续投递；否则写 `.restart` 并 block 一个 `IDLE_TICK`。
`supervisor.js` 每 2s 轮询 `.restart`，见到就 SIGTERM 掉 `claude`，子进程 exit 后 2s 重新 spawn（`claude --model <m> --dangerously-skip-permissions <prompt>`）。
README 希望每条消息使用新 session，但 backlog 分支可以沿用当前 session，见下。空闲时 hook 使用 `IDLE_TICK`，并检查 `HEARTBEAT_INTERVAL`（默认 60s）阈值；另有 watchdog（`WATCHDOG_TIMEOUT` 默认 300s，`.last-tick` 过期则杀）与 orphan reaper。
relay 是**独立的可选 outbox 桥**：`relay/relay.js` 按 offset 轮询 `io/outbox.jsonl`，把 `{action:'send',channelId,content}` 经 discord.js 发出（也支持 `typing`、`files`）。

**分类与限定**：这是**外部 supervisor 驱动的自主 turn**（不是 CC 原生 heartbeat，也不是 MCP channel），目标是「一条消息一 session」的**无状态**处理。
但**代码并不保证**每个 backlog 消息获得独立 session：当 `.responded` 存在时，hook **先 `checkInbox()` 再 `block(next)`，然后才写 `.restart`**——
若上一轮后已有 backlog，这一条会在**同一 session** 内被投递并继续，`.restart` 只在没有下一条时才写。故「one message = one fresh session」是 README/注释的**意图**，非实现保证。
空闲行为也非「固定 60s 一次模型调用」：当距 `.last-tick` 不足 `MIN_INTERVAL` 时，代码 `sleepSecs(15)` 后**仍可 `block(IDLE_TICK)`**；`HEARTBEAT_INTERVAL` 是分支判断阈值，**不保证 60s 调用间隔**。
且 Stop hook 的 `block` 依赖 CC 的 Stop continuation 机制；**当前 CC 的 Stop 连续上限**（见 [Heartbeat / channels](heartbeat-and-channels.md)）意味这套「无限循环」旧兼容性**未测**。
另：offset 推进只是**收据式消费**（读完即写），**不证明模型已处理**该消息——若进程在投递后崩溃，该行不会重放。
空闲 tick 的设计用途是保活；模型是否安静结束仍须行为验证。
README 的 billing 说法（`-p`/SDK 计费桶 vs 订阅）是**作者主张**，当前计费政策超出本次范围，本文不背书。

## 来源 2 — vectorize-io/hindsight（passive recall：hook 在模型前召回并交付）

revision [`f7dd3f4f`](https://github.com/vectorize-io/hindsight/tree/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066)（commit 2026-10-02）。
实读：`README.md`、`hooks/hooks.json`、`scripts/recall.py`（292L，全）、`scripts/lib/client.py`、`config.py`、`state.py`、`content.py`、`bank.py`、`setup_hooks.py`、`tests/test_hooks.py`。未审 backend / MCP / daemon 全链。

**结论（有证据）**：hook **自身**在模型前召回并**为模型输入交付正文**，属 passive recall。
`UserPromptSubmit` 绑 `recall.py`（timeout 45s）；`recall.py` 读 stdin 的 `prompt`（也接受 `user_prompt`），
`recallContextTurns>1` 时读 `transcript_path` 拼多轮 query，截断到 `recallMaxQueryChars`（默认 800），
调 `client.recall(bank_id, query, max_tokens=recallMaxTokens=1024, budget=recallBudget='mid', types=['observation'], timeout=10)`
（`client.recall` 默认 `timeout=10`，可被 `requestTimeoutSeconds` 覆盖）；把结果包成 `<hindsight_memories>…</hindsight_memories>`，
经 `hookSpecificOutput.additionalContext` 输出 → 进入**模型输入**。`additionalContext` 在**普通 UI** 不可见，**不等于**不落盘：
该内容仍可能进入磁盘 transcript，其持久化与清理见 [Context retention](context-retention.md)。`recallMinScores` 在交付前按分数丢结果（缺失/None 分数 fail-open）；
无结果则**不输出**。README 说的「12 秒超时」与 hooks.json 的 45s / `client` 的 10s 并存——**以实测 runtime 为准，本轮未跑**，故只记录各层声明。
这三层各指不同预算：**45s 是 hook 进程时限**、**默认 10s 是单次 HTTP 调用超时**，二者**并不天然冲突**；README 的 12s 是**文档漂移**。

**去重/预算**：`recallAdditionalBanks` 用 `seen_banks` 跳过已回召的 bank；`recallTypes`/`recallMaxTokens` 等仅为**配置默认值**，反映**意图**（如只取已合并的 `observation`），**不代表**已验证的重复结果抑制。
`recallAdditionalBanks` 会增加总耗时，故总 elapsed 可不同于单次 10s 预算。auto-recall 默认 `true`，可整体关；去重/预算细节不作为已验证行为。

## 来源 3 — zilliztech/memsearch（反例：自动日志注入 vs 召回提示，两者分开）

revision [`2a4652fa`](https://github.com/zilliztech/memsearch/tree/2a4652fa086fbd45e92bfd8da7781ebe1642baa7)（commit 2026-09-24）。
实读：`plugins/claude-code/README.md`、`hooks/hooks.json`、`hooks/session-start.sh`（337L，全）、`hooks/user-prompt-submit.sh`（21L，全）。未审 `memory-recall/SKILL.md`、`stop.sh`、`transcript.py` 与 CLI。

这里**恰好把两类机制拆开**，是要点：

- **SessionStart = 自动 context（passive）**：`session-start.sh` 找 `MEMORY_DIR` 下**最近 2 个** daily log，各取最多 40 行、总量 ≤**脚本自身**的 `RECENT_MEMORY_MAX_BYTES=1800`，
  拼成 `# Recent Memory` 经 `hookSpecificOutput.additionalContext` 输出，作为**最近历史**的冷启动注入。这里注入的是**历史记录**，**不一定**是当下实时 state。
  1800B 是**本脚本自己的上限**；其上注释的「CC 对 inline hook `additionalContext` 约 2KB 截断」是该快照下的**作者观察**，**不是当前官方 CC 限制**——
  当前 live hook 限制与目标 build 需**各自取证**。这**不是**检索。
- **UserPromptSubmit = 用户可见提示（不是 passive recall）**：`user-prompt-submit.sh` 只在 prompt ≥10 字且 `memsearch` 可用时回
  `{"systemMessage": "[memsearch] Recall available if needed"}`——**只返回一行能力提示、不检索、不交付记忆正文**。官方把 `systemMessage` 定义为用户可见消息，不能把它当作已注入模型的提醒。[Hooks JSON output](https://code.claude.com/docs/en/hooks#json-output)；README 描述真正检索由模型选择 `memory-recall` skill（`context: fork` 子代理）；其 skill 正文未读。

**分类限定**：SessionStart 的 recent-log 注入是 passive 自动 context（自动最近日志注入）；UserPromptSubmit 的输出是用户可见 hint；README 所述 skill 才是 **model-invoked** 召回路径，
**不得**把 hint 标成被动检索或模型已收到的 context。README 的 3-layer progressive disclosure / fork 说明是**作者描述**，本轮只核了 shell 证据，skill 正文未读。

## 来源 4 — kagamiurayama/claude-code-roof-mod（已供上下文的**转换**，非 present state 生产者）

本地快照 revision [`888dceb8`](https://github.com/kagamiurayama/claude-code-roof-mod/tree/888dceb88631186dfcf01d69b088bedec9c1009a)（commit 2026-10-02，复用 `references/upstreams.json`）。
实读：`README.md`、`roof-mod/hooks/register.js`、`probe-mod/hooks/register.js`、`fragments.js`、两个 JSON。未重做 prompt-stripping / reminder override 审阅。

**分类**：roof-mod 是**对已经供给的 context 做转换**（Mods `prompt.attachment` / `prompt.context`），**不是 present state 的生产者**——
它不产生当下状态、不召回、不唤醒，只改已存在注入的正文；输入正文与来源元数据由事件给出（`e.text`、`origin.kind`∈`engine|hook|plugin`），
未见更上游 request prefix/suffix，也**无**自主 turn 机制。

**engine-origin 限定（重要）**：`origin.kind === 'engine'` 只表示「这条提醒由 engine 渲染」，**engine 写出的正文里可以夹带第三方原文**
（用户 @ 的文件、hook 输出、转发消息原文等）——本 repo 既有研究已确立「engine 生成的消息仍可能包含外部原文」（见 [current state](current-state.md)）。
因此 roof-mod `rewriteProse()` 虽按 `origin.kind` 过滤，**不等于**正文只含 Claude Code 自有文字；probe 自述「日志里有提醒原文，可能带邮箱、路径」正是同一事实的另一面。

**weather/location**：所读文件**无** weather/location 注入实现。**明确记录为缺失**，不以「模型自己调用天气工具」替代——那是 model-invoked tool call，不是 passive present context。

## 来源 5 — CyberSealNull/CcCompanion（scheduled companion push，README/手册层）

revision [`bbe5faac`](https://github.com/CyberSealNull/CcCompanion/tree/bbe5faac0708af34f8ff3b31ed2a4a1720c3d283)（commit 2026-07-23）。实读：`docs/HEARTBEAT_HOWTO.md`（127L，全）。`README.md` 仅作背景。

这是**应用层 scheduled companion push**：用户自建 `~/scripts/heartbeat.py`，由 **launchd `StartInterval=3600`（每小时）** 触发，
脚本**直接起独立 Anthropic 客户端**发起一次 API 判断（illustrative prompt 用**固定的时间/上条消息**示例，不是真实历史），
回答 `SPOKE: …` 则把文本 POST 到本地 `http://127.0.0.1:8795/chat/append`（`source:"heartbeat"`），由 ccc 的 APNs server 推给 iPhone；`SILENT:` 则不发。

**分类与限定**：这条链**不经过 Claude Code 会话、不是原生 CC heartbeat**，也不是定期唤醒一个持续 companion 进程；
它是一次性外部判断 + 本地 chat 追加。手册明说**真实历史、quiet hours、dedupe 都只是「进阶」建议（未实现）**；
其固定时间/上条消息为**示意性**，**不代表作者私有的生产 job 内容**。我方**未执行任何代码**。

## 来源 6 — callie0313/dylan-heartbeat（wake-time 天气/location + prompt 打包比较器）

revision [`32ec7d51`](https://github.com/callie0313/dylan-heartbeat/tree/32ec7d51c7c60f80f20d7caa4647c0a85c5a651f)（commit 2026-08-10）。实读：`README.md`（619L，全）、`wake_up.js`（644L，全）。未读 `server.js` 全链。

**它不是 CC 插件**：架构是 Kelivo 客户端 → 自有 Gateway（`server.js`）→ 上游 LLM API；`wake_up.js` 是**定时唤醒 runtime**：
按 `DAY/NIGHT_CHECK_INTERVAL_MINUTES`（默认白天 10min / 夜间 2h）自调度，`shouldWake()` 依 `DAY/NIGHT_WAKE_AFTER_MINUTES`（60/120min）决定，
读 `enhanced_messages.json` 时间线、`getLastUserTime()` 算间隔，然后 **`fetchWeatherContext()`**：
`WEATHER_ENABLED=false` 默认关；开启且 `WEATHER_LAT/LON` 有效时请求 **Open-Meteo** `https://api.open-meteo.com/v1/forecast`
（`current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m`，`daily=sunrise,sunset`，`timezone=auto`，5s 超时），
把结果排成 `## 天气信息` 文本块。

**何时算可以醒**：`getLastUserTime()` 从 timeline 的 user 正文解析最近可识别的时间，`shouldWake()` 将距今分钟数与阈值比较。所读路径使用的是消息间隔，没有提供主聊天 `turn_busy` 或显式 `chat_active` 锁；因此不能把它说成已证明“主聊天活跃时绝不会并行唤醒”。同文件的 `HEARTBEAT_URL` POST 是运行状态上报，也不能当成一次模型自主活动。

**prompt 打包 / request 组装（source 阅读，非实测）**：`buildWakePrompt(currentTime, diffMinutes, weatherContext)` 优先级 `wake_prompt.txt` → `WAKE_PROMPT_TEMPLATE` env → 内置默认；
把 `${currentTime}`/`${diffMinutes}`/`${weatherContext}`（=`${weather}`）替换进去。`runWakeUp()` 组装 `wakeMessages`：
`system` = `[wakePrompt, cleanSP]`（cleanSP 为时间线首条 system 去掉 `## Memories` 后），`user` = 一段**最近记录文本**（显式标注「这不是实时对话、用户没发消息、你处于后台自主唤醒」）；
再 `POST TARGET_API_URL`（`temperature:0.8`、`top_p:0.95`、`stream:false`）。**保留结果（读取到的意图，非端到端保证）**：模型输出若非 `[NO_ACTION]` 则推送（Bark/ntfy，正文截 500 字），
`runWakeUp()` **尝试**把一条事件记录 `POST` 到 `GATEWAY_URL` 并 catch 写失败——**该函数不直接写本地时间线，也不能从 POST 尝试推出可靠持久化**，写失败只记录日志。成功拿到模型响应后可记录 sent/silent/empty/diary-only/push-failed 等结果；
但**上游模型请求出错会在到达该阶段前抛出**，故**并非每种失败都被保留**。`server.js` **未审**。可选 `[DIARY]…[/DIARY]` 存 `diary/YYYY-MM-DD.md`。

**分类与限定**：这是 **Kelivo / gateway 架构**（用户自述「Gateway 不修改 Kelivo 人格，只在正确时间位置注入自主行为」），
**不是原生 CC 兼容**；`weatherContext` 是**由机制请求并注入**的 present context（passive），**不是**给模型的天气工具。我方**未做 weather/API/model 调用**。

## 对照小结（仅就可读证据）

| 来源 | 非提示自主 turn | 自动供给的 context | 被动记忆召回 | 证据层级 |
| --- | --- | --- | --- | --- |
| Siigari/claude-heartbeat | 有：外部 supervisor 驱动 Stop→inbox→restart/outbox（backlog 可共享 session，非严格一消息一 session） | 无 | 无 | source 检视 |
| vectorize-io/hindsight | 无（hook 非调度器） | 有：`UserPromptSubmit` hook 前召回并交付正文 | **有（passive）**：`additionalContext` 注入 `<hindsight_memories>` | source 检视 |
| zilliztech/memsearch | 无 | 有：`SessionStart` 注入最近日志（自动 context，recent-history，≤1800B / 40 行 / 2 文件） | UserPromptSubmit 只给用户可见 hint；README 描述另有 **model-invoked** skill | source 检视 |
| kagamiurayama/claude-code-roof-mod | 无 | **转换器**（改已有 `prompt.attachment`/`prompt.context`），非生产 | 无 | source 检视（本地快照） |
| CyberSealNull/CcCompanion | 有：launchd 每小时 + 独立 API 判断 + `/chat/append`（应用层，非 CC） | 无（示意固定 prompt） | 无 | README 手册层（无代码执行） |
| callie0313/dylan-heartbeat | 有：自调度 wake runtime（Kelivo/gateway，非 CC） | 有：Open-Meteo 天气注入唤醒 prompt（默认/请求意图，非端到端交付保证） | 无 | source 检视（未实呼） |

## 未验证与限制

- 全部为**静态 source / README 检视**：无安装、无 hook 运行、无模型/天气服务调用、无 runtime 证据。
- hindsight 的 45s(hook 进程)与 10s(HTTP 调用)属不同层、不天然冲突，12s 为文档漂移；均未在 runtime 对齐；去重只从配置默认值推断（意图，非已验证抑制）。
- memsearch 的 `memory-recall` skill 正文、`stop.sh`、transcript 流程未读；3-layer 属作者描述。
- memsearch 的 1800B 为脚本自设上限；「CC ~2KB 截断」是该快照的作者观察，当前 live hook 限制与目标 build 需另证。
- roof-mod 为本地快照、无 runtime；weather/location「无实现」仅针对所读文件。
- CcCompanion 属**手册层**，其固定时间/上条消息为示意，不代表作者私有生产 job；未执行其代码。
- dylan-heartbeat 为 Kelivo/gateway，非原生 CC 兼容；未发起天气/模型请求；`server.js` 未审，事件写回是 POST 尝试，持久化保证未证。
- Siigari 的 backlog 共享 session、空闲 tick 时机、offset 收据语义与 Stop 连续上限兼容性均来自 source 阅读，**未在 runtime 验证**。
