# Heartbeat、scheduled wake 与外部 channel

本页解释实现机制。研究的使用语境是持续的伴侣相处：自主醒来可以用于回想、兴趣、内部活动、主动表达，也可以安静结束；不要求每次醒来都完成任务或通知用户。整体问题与 ambient context、自动召回、输入包装的关系见 [Companion context](companion-context.md)。进程存活检测只作为术语对照。

观察日期：2026-10-05（Asia/Singapore）。本文是**公开材料研究**，不新增 daemon、不创建心跳 job、不联系外部 channel。所有条目分成“官方文档/官方生成 types 描述”与“本机实跑”，本轮**没有**真实 request、scheduler 或 channel 实跑。版本与来源清单见 [references/heartbeat-sources.json](../references/heartbeat-sources.json)。

本轮已直接取到 5 个官方页面（URL 与读取状态见 reference JSON）。上一轮因网络失败只据 types/changelog 的默认值、持久化、expiry、busy、idle、delivery、permission relay 等结论，已用这些页面逐条校准；历史网络失败记录保留在 `.cache/`，不作为当前状态。另有目标 build **2.1.289** 在 synthetic 本地 slash-command 会话中生成的官方 declarations（`.claude-plugin/types/claude-code/index.d.ts`、`claude-code-tools/index.d.ts`），用于替换旧 2.1.277 的字段依据。**声明可用 ≠ scheduler/channel 实跑。**

## 一个先决区分：tick / 唤醒 ≠ 模型调用 ≠ 消息交付

“心跳”在工程上被用在很不同的地方。研究 context 生命周期时至少要分清五层，它们各自的成功条件互不蕴含：

| 层 | 是什么 | 不能从它推出 |
| --- | --- | --- |
| 进程 liveness heartbeat | 进程/worker 周期性证明还活着 | 有 turn 在跑、上下文被重建、消息已交付 |
| 定时 tick / 唤醒计划 | 一个到点要触发的“唤醒条目” | 模型被调用、prompt 已进入 request、结果可见 |
| agent 自检/唤醒一轮 | 唤醒后真的起了一个 turn，把存储的 prompt 交给模型 | 该 turn 完成、交付成功、无自燃循环 |
| 消息到达唤醒 | 外部/本地 channel 或 peer 的入站消息把 session 从 idle 拉起 | 消息被模型读到、被批准、被回复 |
| 外部通知 / 交付 | 把结果推给用户或外部系统 | 与前面的 tick 一一对应；交付失败可触发重试 |

官方 [Changelog](https://code.claude.com/docs/en/changelog) 的不同版本分别记录过 SDK 工具进度 heartbeat 丢失，以及 scheduled tasks / `/loop` 在交付失败后每秒重复触发的修复。这是不同机制的历史缺陷，不能把旧故障当作当前默认行为。**调度是 tick，交付是另一层**；见下 OpenClaw 的 delivery/retry 段。

## 官方 Claude Code：scheduled tasks / `/loop` / cron

来源：[Run prompts on a schedule](https://code.claude.com/docs/en/scheduled-tasks)（2026-10-05 直接读取）。

### 三种排程机制（官方对比表）

官方页面给出三种 “recurring / one-off work” 的选择，并明确其持久化与权限差异：

| | Cloud（Routines） | Desktop scheduled task | `/loop` |
| --- | --- | --- | --- |
| 运行位置 | Cloud，默认 Anthropic 托管 | 本机 | 本机 |
| 需要机器开机 | 否 | 是 | 是 |
| 需要开着 session | 否 | 否 | **是** |
| 跨 restart 持久 | 是 | 是 | 仅 `--resume` 恢复，有例外 |
| 访问本地文件 | 否（fresh clone） | 是 | 是 |
| MCP | 每任务配置 connector | 配置文件 + connector | 继承 session |
| 权限提示 | 否（自主运行） | 每任务可配 | 继承 session |
| 最小间隔 | 1 小时 | 1 分钟 | 1 分钟 |

结论：**Routines/Desktop 是独立于 session 的调度，`/loop` 是 session-scoped**。研究时不能把“云端 routine 跨 restart 存活”当成“本地 cron 也会”。`/schedule`（别名 `/routines`）走的是 cloud routine 路径（[Commands](https://code.claude.com/docs/en/commands)）。

### `/loop` 的公开行为

- `/loop` 是 bundled **skill**（prompt-based），三种输入组合：`interval + prompt` 走固定 cron；只有 prompt 时由 Claude 每轮在 **1 分钟~1 小时**之间自选延迟；只有 interval 或什么都不给时跑内置 maintenance prompt 或用户的 `loop.md`。
- **固定 interval**：把 interval 转成 cron 表达式；单位 `s/m/h/d`；秒会被向上取整到分钟（cron 一分钟粒度），`7m`、`90m` 这类不干净的步长会被舍入到最近的合法步长并告知所选值。
- **`loop.md`**：`.claude/loop.md`（项目级，优先）或 `~/.claude/loop.md`（用户级），替换内置 maintenance prompt；只在命令未给 prompt 时生效；编辑在下一次迭代生效；**超过 25,000 bytes 会被截断**。
- **停止**：self-paced loop 等待下一轮时按 `Esc` 清掉 pending wakeup；Claude 也可用 `ScheduleWakeup { stop: true }` 结束；某一轮既没重排也没停止时，CC 兜底安排一次约 **20 分钟**后的 wakeup，若那次仍不重排则结束。固定 interval loop 一直跑直到取消或 7 天到期。
- **Provider 差异**：动态 interval 与内置 maintenance prompt 在每个 provider、甚至关闭 feature-flag fetching 时都可用（Bedrock/Vertex 等或关闭 fetching 时需 v2.1.248+）。

### 定时如何执行（校准 busy / idle / 重试）

直接来自官方页面，修正上一轮“只据 changelog”的措辞：

- **scheduler 每秒检查** due tasks，并 **low priority 入队**；scheduled prompt 在 turns 之间触发，busy 时 **defer 到当前 turn 结束**。
- **无 catch-up**：长请求期间错过多个 interval，恢复 idle 后只触发一次，不逐个补跑。
- **jitter**：避免所有 session 同一墙钟时刻打 API。recurring 最多晚 **30 分钟**（高于每小时的则最多半个 interval）；one-shot 若排在整点/半点，最多 **早 90 秒**。offset 由 **task ID 派生**，同一任务总是同一 offset。想避开就选非 `:00`/`:30` 的分钟（例如 `3 9 * * *`），one-shot jitter 即不适用。
- **7 天 expiry**：recurring task 创建后 **7 天自动过期**；它**最后一次触发后自删**。需要更久就到期前取消重建，或用 Routine/Desktop。
- **时区**：所有时间按**本地时区**解释，`0 9 * * *` 是本地 9am，不是 UTC。
- **cron 语法**：标准 5-field；支持 `*`、单值、`*/15`、`1-5`、逗号列表；**不支持** `L`/`W`/`?`/`MON`/`JAN` 之类扩展；day-of-month 与 day-of-week 同时受限时按 **vixie-cron OR 语义**。
- **`CLAUDE_CODE_DISABLE_CRON=1`**：完全关闭 scheduler，cron 工具与 `/loop` 不可用，已排程的任务停止触发（与 [Environment variables](https://code.claude.com/docs/en/env-vars) 一致）。

### 持久化（校准上一轮的 `durable` 措辞）

- 官方页面：**session-scoped**。`--resume`/`--continue` 会恢复**未过期**的 `CronCreate` 任务，但“except recurring tasks that have expired and one-shot tasks whose scheduled time has passed”。
- **self-paced `/loop` 不恢复**，要重新跑 `/loop`。Background Bash 与 monitor 任务**从不恢复**。Backgrounding the session 会把 `/loop` 带到后台 session 继续跑。
- 跨 session 保存时（feature-flag fetching off 的路径）：任务存在项目的 `.claude/scheduled_tasks.json`；`.claude` 目录或该文件是 symlink 时**返回错误**而不排程；保存的任务**只在创建它的项目文件夹里运行**，复制到别的文件夹（如新 worktree）会在那里**列出但不运行**。
- **声明与文档保留一项待核差异**：2.1.289 `CronCreate.durable` 注释称默认 `false` 仅内存、`true` 才写文件跨 restart；当前文档则直接承诺 `--resume`/`--continue` 恢复合条件的 CronCreate 任务，未限定必须 `durable:true`。session 恢复与跨 session 文件持久化应分别记录，不能从注释推出“只有 durable 才能恢复”；feature-flag 分支和实际恢复行为未实测。changelog 中复制文件的修复只补充历史背景。

### 上限与管理工具

- 每个 scheduled task 有 **8 字符 ID**（传给 `CronDelete`）；一个 session 最多 **50** 个 scheduled task（文档；`CronList` 声明未见上限字段）。
- 底层工具：`CronCreate`（5-field cron + prompt + recurring 与否）、`CronList`、`CronDelete`。目标 build 2.1.289 的生成声明与 2.1.277 公开声明在这些字段上**完全一致**（见下）。

## 官方 Claude Code：Channels（外部 channel）

来源：[Push events into a running session with channels](https://code.claude.com/docs/en/channels)（2026-10-05 直接读取）。

- **定位**：channel 是**一个把事件推入正在运行的 session 的 MCP server**，所以 Claude 能对“你不在终端时发生的事”作出反应。可双向：Claude 读事件后**经同一 channel 回复**（chat bridge）。**事件只在 session 开着时到达**；要做 always-on 就把 CC 跑在后台进程/常驻终端。
- **与轮询/新 session 的区别**：事件到达**你已打开的那个 session**，不是 spawn 全新 cloud session、也不是等被轮询。
- **research preview**：需要 claude.ai 或 Console API key 的 Anthropic 认证；**Bedrock / Google Cloud Agent Platform / Microsoft Foundry 不可用**；Team/Enterprise 需管理员显式启用。预览期 `--channels` 与 `--dangerously-load-development-channels` **不出现在 `claude --help`**，但可用。
- **安装与接线**：channel 作为 plugin 安装（`/plugin install telegram@claude-plugins-official` 等）；带 token 的 configure 命令把凭据存到 `~/.claude/channels/<name>/.env`；重启时用 `claude --channels plugin:<name>@<marketplace>`；Telegram/Discord 用 pairing code 把发送者加进 allowlist。官方预览内置 Telegram、Discord、iMessage；附 fakechat 本地 demo（`http://localhost:8787`）。channel plugin 需要 **Bun**。
- **入站如何被模型读**：终端显示成 `← fakechat · web: …` 的 inbound channel line，而**模型收到的是 `<channel source="plugin:fakechat:fakechat">` event**，用 plugin 的 scoped server name。这不是用户本人发言，选材时必须区分。
- **回复可见性**：Claude 经 channel 回复时，**终端只显示 tool call 与确认（如 "sent"），回复正文出现在对方平台**；本端看不到回复文本。
- **权限**：若 Claude 在你不看终端时遇到 permission prompt，session **暂停直到你回应**。声明了 **permission relay capability** 的 channel server 可把 prompt 转发给你，让你远程 approve/deny（已补读 [Channels reference](https://code.claude.com/docs/en/channels-reference) 的 capability、通知格式、reply tool 与 permission relay 字段；未运行示例）。非交互 `-p` 下，需要终端输入的工具（多选题、plan mode approval）被禁用，session 不会卡住。

### 入站信任与权限转发（校准 permission relay）

官方安全段明确：

- **每个已批准的 channel plugin 维护 sender allowlist**：只有你加入的 ID 能推消息，其他一律静默丢弃。Telegram/Discord 走 pairing；iMessage 给自己发消息自动绕过，其他联系人用 `/imessage:access allow` 添加。
- **`--channels` 是每 session 的额外门**：“Being in `.mcp.json` isn't enough to push messages: a server also has to be named in `--channels`.”
- **allowlist 同时 gate permission relay**：在 channel 声明该能力时，获准通过 channel 回复的人也能批准或拒绝工具使用；这两种权限共用 sender allowlist。
- **企业控制**（managed settings，用户不可覆盖）：`channelsEnabled` 是 master switch（必须在任何 channel 交付前为 true；**关闭时连 development flag 一起挡住**）；`allowedChannelPlugins` 决定哪些 plugin 能注册（设置后取代 Anthropic 维护的 allowlist；空数组阻止 allowlist 内的 plugin，但 `--dangerously-load-development-channels` 仍可为本地测试绕过——要**连 development flag 一起挡**就留 `channelsEnabled` unset）。claude.ai Team/Enterprise 默认**阻塞**直到 Owner 启用；Console API key 认证默认**允许**，但组织部署 managed settings 后也需显式启用。Pro/Max 无组织则跳过这些检查。启动时若传了不在名单的 plugin，CC **照常启动但 channel 不注册**，启动提示说明原因。
- **协议坑**：在 v2 MCP client runtime 上，若 channel server 协商到 **protocol revision 2026-07-28**，CC **不注册该 channel server**（[MCP](https://code.claude.com/docs/en/mcp#push-messages-with-channels)）。


### 入站包装与交付层级

server 的 `instructions` 是连接时 context；通知 `content` 进入 channel 标签正文，`meta` 进入属性，原话与路由 metadata 因此是两种载荷。通知写入 transport 没有处理 ack；busy 时多条可合并在下一轮交付。回复由 server 暴露的 MCP tool 完成。见 [Channels reference](https://code.claude.com/docs/en/channels-reference#notification-format)。自定义 terminal bridge 的包装需另追 producer，不能套用这条 native channel 合同。

## 目标 build 2.1.289：生成声明对既有 claim 的校准

证据：[目标 build 记录](target-runtime.md) 中的 `claude-code` / `claude-code-tools` 声明，首行标明 2.1.289。原始文件留在本地 cache。这是**官方生成声明**（synthetic 本地会话，无真实模型调用），针对本主题只核了相关 symbol。

| 断言 | 2.1.289 生成声明 | 与 2.1.277 公开声明的关系 |
| --- | --- | --- |
| `UserPromptSubmitHookInput.source` 可选字段 | `'user' \| 'sdk' \| 'system' \| 'loop_wakeup' \| 'schedule_wakeup' \| 'poll_event'`；推广期间可缺省 | **一致**（保留 poll_event 的 delivery-ack 说明） |
| `Stop` / `SubagentStop` 输入 | 含 `background_tasks?: BackgroundTaskSummary[]`、`session_crons?: SessionCronSummary[]` | **一致** |
| `SessionCronSummary` | `id/schedule/recurring/prompt`（prompt 截 1000 字符） | **一致** |
| `CronCreate` 工具输入 | `cron`/`prompt`/`recurring?`（默认 true，7 天过期）/`durable?`（默认 false） | **逐字一致** |
| `ScheduleWakeup` 工具输入 | `delaySeconds?` clamp `[60,3600]`、`reason?`、`prompt?`（verbatim，sentinel `<<autonomous-loop-dynamic>>`）、`stop?`、`noop?` | **一致** |
| `PromptOrigin.kind` | 含 `channel`（带 `server`）、`scheduled-trigger`、`task-notification`、`peer`、`peer-send-message`、`slack-ping` 等 | **一致**（仍是主要分类面） |
| `SessionReceiveOrigin.kind` | `'bridge' \| 'task-notification' \| 'scheduled-trigger' \| 'peer-send-message' \| 'projects-relay' \| 'slack-ping' \| 'unclassified'`，另有 `'peer' \| 'coordinator'`（带 `plugin?` / 团队 `teammate`/`isVerified` 变体） | **有变化**：2.1.289 的 `SessionReceiveOrigin` **不再含 `channel`**；`peer`/`coordinator` 细化为带 `plugin`、`teammate`、`isVerified` 的变体，并新增 agent-team mailbox 来源 |

在本次比较的 symbols 内，主要差异是 `session.receive` 的 `origin` 分类：`channel` 不再出现在 receive union，而 `PromptOrigin` 仍有它；不能据此推导 channel 已停用。`peer`/团队 mailbox 来源细分，`plugin` 仍是发送方声称的名字，不能用它作权限判断；`isVerified` 区分本进程 harness 写入与未核实的 inbox 文件来源。

## 官方 Claude Code：cross-session messaging 与其它入站通路

除 MCP channel 外，本机进程间还有一条通路（不是 MCP channel，分类也不同）：

- `CLAUDE_CODE_MESSAGING_SOCKET` / `CLAUDE_CODE_MESSAGING_TOKEN`：session 绑定 inbox socket 时由 CC 自己 export 给 hooks/Bash；其它 session 向该路径投递，消息经过本 session 的 **inbound controls**；settings `env` block 不能设置它们（[Environment variables](https://code.claude.com/docs/en/env-vars)）。
- `refuse inbound` 的 session 在 `session.receive` **之前**就拒收（hook 看不到）；**held 等批准**的消息先到 hook，mod 能读到“用户还没批准”的消息；受 `CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS` / `dialogExpiry` 约束（[Mods API](https://code.claude.com/docs/en/plugins/mods/api)）。
- `SendMessage.notify_when_idle`（2.1.289 声明）：可选地让另一台本机 session 在它**下次 idle 或退出时**给你一次 notice——一次性、无轮询的订阅，是“idle 触发交付”的另一条公开面。

与 cron 的区别：cross-session messaging 是**对方投递**唤醒（`peer`/`peer-send-message`），cron 是**自己到点**唤醒（`scheduled-trigger`）。这些机器注入路径也会触发 `UserPromptSubmit`（[Hooks](https://code.claude.com/docs/en/hooks)：scheduled task firing、background subagent reporting、another session's message 都会跑 `UserPromptSubmit`），但选材/清理策略不同。

## OpenClaw 对照：heartbeat vs automations（scheduler）

来源（2026-10-05 直接读取，均为官方文档）：[Heartbeat](https://docs.openclaw.ai/gateway/heartbeat)、[Automations](https://docs.openclaw.ai/automation/cron-jobs)、[Automation（cron vs heartbeat）](https://docs.openclaw.ai/automation/cron-vs-heartbeat)。

> **覆盖限制**：`automation/cron-jobs` 是**索引页**，busy/coalescing/persistence/delivery 等细节分散在其 child 页面（`cron-jobs/how-it-works`、`schedules`、`payloads`、`delivery`、`managing-jobs`、`webhooks`），这些 child 页**本轮未取到**。下面只写这三个已读页面**实际写到**的项，不补不存在或缺页的字段/默认。

### 两种机制的分工（官方口径）

- **Heartbeat** 是一个**系统拥有的 monitor automation**，用 **periodic agent turns** 在**主 session**里跑，好让模型能主动 surface 需要注意的事项而不刷屏。ACP、subagent 与 isolated automation 各有自己的执行 owner。
- **Automations** 是 OpenClaw 的内建 scheduler：持久化 jobs、到点唤醒 agent、可把输出交付到 chat channel、webhook 或**什么都不发**（nowhere）。管理命令是 `openclaw automations`，`openclaw cron` 是其别名。
- 官方对比表（cron-vs-heartbeat 页）：

| 维度 | User-authored automations | Heartbeat monitor automation |
| --- | --- | --- |
| Timing | one-shot、interval 或 cron 表达式 | scheduler 拥有的 interval，**默认 30min** |
| Session context | isolated、current、named 或 main session | **main session，可选 isolated** |
| Delivery | channel、webhook 或 silent | owner-routed alerts 或 silent |
| 适合 | 明确报告、提醒、recurring work | ambient monitoring 与事件 follow-up |

「两者共用同一 Automations scheduler」；heartbeat cadence **实际由 scheduler 拥有**（gateway 为每个 heartbeat-enabled agent 维护一个 system-owned automation job，在 `openclaw cron list --all` 里显示为 `Heartbeat (agent-id)`）。**心跳配置是 desired-state 输入，持久化的 monitor schedule 才拥有实际 tick 与 runner cooldown**。

### 与 CC 的结构性对照

| 关注点 | Claude Code `/loop` + `CronCreate` | OpenClaw heartbeat | OpenClaw automations |
| --- | --- | --- | --- |
| 执行主体 | session 内的 scheduler（每秒检查、low priority） | 主 session 的周期 turn（默认 30m） | scheduler job（isolated/current/named/main） |
| 默认 cadence | 无默认；`/loop` 固定或自选 | 30m（OAuth/token 认证时 1h） | 每 job 自定 |
| busy 时行为 | defer 到 turn 结束；missed 折叠为一次 | defer（见下） | （child 页，未取） |
| no-op / quiet | `ScheduleWakeup.noop`；连续 no-op 折叠 | `NO_REPLY`；`heartbeat_respond notify:false`；`HEARTBEAT_OK` 抑制 | 可 silent delivery |
| 跨 restart | 文档承诺 resume 恢复合条件任务；与 durable 注释差异待实测 | monitor 行由 gateway 启动/config reload 时写入 | 持久化（本页陈述） |
| 交付目标 | session 内注入 prompt | owner DM / `last` / 指定 channel / `none` | channel、webhook 或 nowhere |
| 外部触发 | Channels（MCP push） | event-driven wake（background exec completion 等） | inbound webhooks / Gmail PubSub |

### Heartbeat 的 busy / coalescing / quiet / idle（校准）

官方 heartbeat 页明确写到的项（未写的不推断）：

- **默认值**：interval `30m`；应用 Anthropic provider 默认在解析为 OAuth/token 认证（含 Claude CLI reuse）时升为 `1h`，**仅当 `heartbeat.every` 未设**。`0m` 关闭 recurring cadence（automation job 仍在但 disabled；targeted event-driven wake 仍可跑一次 turn）。
- **planned cadence 与 tick 分离**：配置改动由 gateway 在启动与 config reload 时写入；保存 monitor 行失败时 gateway 保留已接受的 config 并报告需恢复；retry 用**当前已接受**的 config。
- **scheduled heartbeats 依赖 automations**：`cron.enabled=false` 或 `OPENCLAW_SKIP_CRON=1` 时不跑 scheduled heartbeat（记 startup warning），**没有单独的 heartbeat fallback timer**；manual/event-driven wake 仍可用。
- **busy/coalescing**：主队列、automation、同 agent 的运行或目标 session 忙碌时，会按工作类型延后或跳过。 一个**尚未开始准备**、且不带事件的 plain monitor poll 记为 **skipped**，等下一次持久化 cadence tick，而不是把 run 挂在 busy work 后面；带 queued events / scheduled tasks 或已 admitted/retained 的 wake 仍会 **retry**。Immediate/manual wake 绕过 broad same-agent active-run 检查，但仍遵守 main/automation/target-session busy guards。**兄弟 agent 不互相暂停。**
- **coalescing**（文档明述）：Doctor 迁移出的 heartbeat task jobs 可将同时到期的工作合并为一轮；若 completion 与 scheduled work 合并，仍保留后者的 busy guards。
- **quiet / no-op**：默认 prompt 要求无事时回复 **`NO_REPLY`**；`heartbeat_respond` 可用 `notify:false` 静默或 `notify:true` + `notificationText` 报警；**结构化 tool response 优先于文本 fallback**。有意义但 `notify:false` 的结果仍作为**有界 internal context** 记到该 session 下一轮；`no_change` 确认与已确认的可见通知**不**这样保留。legacy `HEARTBEAT_OK` 在**开头或结尾**被接受，且剩余内容 ≤300 字符时整条丢弃；在**中间**不特殊处理。visibility 由 `showOk`/`showAlerts`/`useIndicator`（per-account → per-channel → defaults）控制；**三者全 false 则该 run 整个跳过（无模型调用）**，记 `reason=alerts-disabled`。
- **idle**：heartbeat-only 回复**不让 session 保活**；idle expiry 用 `lastInteractionAt`（最后一条真实 user/channel 消息），daily expiry 用 `sessionStartedAt`。Control UI/WebChat **隐藏** heartbeat prompt 与 OK-only 确认，但底层 transcript 仍可含这些 turn（audit/replay）。
- **delivery/retry**：若 channel readiness check 挡住 alert，OpenClaw **记录 non-delivery**，**一分钟后 grace period 重试**，**不消耗 cadence slot**；该 retry 是**重跑 heartbeat**，不是重放那条 alert。一旦 send 进入 **durable delivery queue**，后续 transport retry 归该 queue 管。被 block/unconfirmed 的 `notify:true` alert 也会被记录（含 alert text 与 delivery reason），作为该 session 的**最新结果**，不是 alert history 或精确重放队列。
- **empty scratch skip**：scratch 存在但“effectively empty”（仅空行、Markdown/HTML 注释、`# Heading`、fence marker、空 checklist 占位）时**跳过 run 省 API**，记 `reason=empty-heartbeat-file`。没有 scratch 时仍会跑，由模型决定。
- **rate limits（targeted event wakes）**：recurring cadence 关闭时，targeted event wake 仍受 per-agent rate limit：**事件 turn 之间最小 30 秒**，以及 **60 秒内 5 次启动后的 flood guard**；guarded deferral 到期后恢复。

### Automations 的持久化 / 交付 / 触发（本索引页实际写到）

- **scheduler 持久化 jobs**，到点唤醒 agent；“can deliver output to a chat channel, a webhook, or nowhere.”
- 支持 **one-shot reminders、recurring interval 与 cron 表达式、inbound webhook triggers**。
- CLI（同一命令组）：`openclaw automations create/get/show/list/runs`；quickstart 示例展示 one-shot reminder（`--at`/`--session main`/`--system-event`/`--wake now`/`--delete-after-run`）。
- **时区**：有独立 [Timezone](https://docs.openclaw.ai/concepts/timezone) 概念页；cron-jobs 的 troubleshooting 有 “Timezone gotchas” 锚点（child 页未取）。
- **已退役的 inferred commitments**：v2026.8.1 移除了从对话里抽取 follow-up 并经 heartbeat 交付的实验；`openclaw commitments` CLI 也没了。**要提醒/排程就建显式 automation**，不会恢复 inferred follow-ups。
- **heartbeat 与 automations 合并面**：`/automation/cron-jobs` 有 `Heartbeat task migration` 锚点；heartbeat 页说明 Doctor 把 scratch 里的 `tasks:` block 转成独立 automation job（保留各自 interval 与上次 last-run 计时）。

**未取到因此不写**：automations 的 run lifecycle/promotion、isolated run hardening、dynamic cadence pacing、payload/session execution styles、unattended run contract、retry 具体策略、webhook 认证、Gmail PubSub 细节——这些都在未取的 child 页。

## 差异表：几种“唤醒 / 通道”机制的选材与清理含义

| 机制 | 触发者 | 公开分类（2.1.289） | 跨 restart | 选材要点 | 清理要点 |
| --- | --- | --- | --- | --- | --- |
| `/loop` dynamic wakeup | 模型自配速 | `loop_wakeup` | 否（进程内，self-paced 不恢复） | 保留 streak/`noop` 状态 | `stop:true` / `Esc`；约 20 分钟兜底 wakeup |
| `CronCreate` recurring | cron 到点 | `schedule_wakeup` / `scheduled-trigger` | 文档 resume 承诺与 durable 注释分别核验 | 保留计划意图与 id | `CronDelete`；**创建 7 天后最后触发并自删**；jitter offset 由 id 派生 |
| `CronCreate` one-shot | 到点一次 | 同上 | 同上 | 保留一次性提醒 | 发后自删；整点/半点最多早 90 秒 |
| routine（`/schedule`） | 云端 | `scheduled-trigger` | 云端 | 与本地 cron 分开记 | Cloud session，不在本机 session |
| 消息到达（cross-session） | 另一 session/agent | `peer` / `peer-send-message`；team mailbox `coordinator`/`peer`(+`isVerified`) | 本机 socket ephemeral | 保留 sender 与是否批准 | refuse/held/timeout 要区分 |
| 外部 channel（MCP） | 外部服务 | `PromptOrigin.kind='channel'`（带 server）；`<channel source=...>` | 取决于 server/plugin | 保留 server；区分“模型收到的 channel event”与用户发言 | 受 `--channels` + sender allowlist + `allowedChannelPlugins`/`channelsEnabled` |
| `asyncRewake` hook | 后台 hook 以 code 2 结束 | system reminder | 未验证 | 保留 stderr，空时取 stdout | 脚本缺失导致反复唤醒是 changelog 已修的旧故障 |
| Stop hook block | 收尾判定 | 延续当前 turn，不是独立 timer | 未验证 | 保留 `stop_hook_active` | 默认 8 次连续 continuation 上限，可配置 |
| OpenClaw heartbeat | scheduler 拥有的 cadence | n/a | monitor 行由 gateway 重写 | 保留 scratch + 最新 internal outcome | `0m` 关 cadence；全 visibility off 跳过 run |
| OpenClaw automation | 用户/自身 schedule | n/a | 持久化 job | 保留 job 定义与 run history | `openclaw automations`；one-shot `--delete-after-run` |

## 为什么这些区分影响选材 / 重试 / 清理

1. **tick ≠ 模型调用。** CC 的 scheduler 每秒检查、low priority 入队；`poll_event` 说明存在“已提交但 delivery ack 还没到”的窗口。把“有 cron 条目”当“已经跑过”会误判状态。OpenClaw 同样把“scheduled cadence tick”与“run 是否真的起 turn”分开（empty scratch / alerts-disabled 都会 skip）。
2. **no-op 与重复 tick。** `ScheduleWakeup.noop:true` 的连续 tick 在终端折叠并计 streak；OpenClaw 用 `NO_REPLY`/`notify:false` 与 `HEARTBEAT_OK` 抑制。清理若把每个 tick 当事件，会把 streak 记成一串进展。
3. **用户新消息优先。** CC 的 busy 任务 defer 到 turn 结束；`idle_prompt` 在用户输入后不发，后台任务在跑或等用量 reset 时也不发。`UserPromptSubmit` 对 cron/loop/peer/channel 也会跑，`source` 可辨 user/sdk/loop/schedule 等大类，但 peer/channel 共用 system，且该字段可缺省；需要结合原始来源，不能从 role 或缺省值猜成用户本人。
4. **已关闭任务。** CC `session_crons[]` 只列“还会唤醒本 session”的条目，空数组只表示此刻没有。清理不能仅凭 Stop 时空数组断言“从没建过”。OpenClaw 的 disabled monitor（`0m`）仍保留 scratch 供再启用。
5. **发送结果未知。** CC cron/`/loop` wakeup 交付失败曾**每秒重发**；channel 入站消息曾首条后静默丢弃；Mods `session.send` 返回 `{isDelivered:false, reason}`。OpenClaw 对 blocked alert **记 non-delivery + 一分钟 grace 重试**（重跑而非重放），durable queue 接管 transport retry。因此“tick 触发”与“消息到达模型”之间必须有独立回执。
6. **权限审批是独立通路。** CC channel permission relay 只在 server 声明该 capability、且 sender 在 allowlist、且 org 未禁用时可用；**能回复的 sender 就能批准动作**。把“能收到消息”当成“能批准”会越权。OpenClaw heartbeat 的 alert delivery 也受 channel readiness/typing/DM policy 单独约束。

## 主聊天、独立活动与触发位置

会话内/外部是触发位置，main/独立 session 是执行目标，same/fresh 是历史策略，channel 是交付去向；四者分别记录。CC 文档的 busy→idle defer 不等于识别“整段聊天结束”。OpenClaw 的 `isolatedSession` 改变输入历史，但同页列出的 busy guards 仍须核对，不能据此断言主聊天活跃时一定并发执行。2026-10-05 已针对这些段落重新核读官方 scheduled-tasks 与 heartbeat 文档，未做运行验证。

本 repo 的 [心跳跳法对照](heartbeat-patterns.md) 将 `chat_active` 与 `turn_busy` 分开；离线实验明确比较聊天活跃时跳过、聊天结束后重判，以及独立自主 session。这是研究候选，不修改上面的平台合同。

## 真实机制的实验判据（待执行）

以下针对真实 CC/OpenClaw 机制，仍仅为**设计**，不是运行结果。另有 [心跳输入包实验](../experiments/companion-input/README.md) 比较显式假设规则；它不验收下列平台行为：

1. **busy defer + 无 catch-up**：构造“任务到点时 Claude mid-response”，断言只出现一次 fire（不是每错过的 interval 一次）且发生在 turn 结束后。
2. **重复 no-op tick**：构造 N 个只改 `noop`/时间戳的连续 `ScheduleWakeup` 回执，断言摘要把 streak 收敛为一条。
3. **来源消歧**：同段文字分别以 `user`、`loop_wakeup`、`schedule_wakeup`、`system`(peer/channel) 注入，断言保留来源标签且不把机器注入升级成用户确认。
4. **交付未知**：模拟“已入队 + `isDelivered:false`”与 OpenClaw 式“blocked alert + 一分钟 grace 重跑”，断言不写“已送达”，区分重跑与重放。
5. **关闭**：`CronDelete` 后条目消失；断言不因“空 `session_crons`”反推“从未创建”。
6. **expiry**：模拟创建后第 7 天的 recurring task，断言“最后一次触发后自删”。

拒绝条件：把 tick、模型调用、交付合并计数；把 channel/peer 注入当用户本人；把空数组当无机制；只用 transcript 增长当交付证据；把 OpenClaw child 页未写的内容当已证默认。

## 读取路径与覆盖

- 直接读取的官方页面（2026-10-05）：[scheduled-tasks](https://code.claude.com/docs/en/scheduled-tasks)、[channels](https://code.claude.com/docs/en/channels)、[OpenClaw heartbeat](https://docs.openclaw.ai/gateway/heartbeat)、[OpenClaw automations](https://docs.openclaw.ai/automation/cron-jobs)、[OpenClaw automation 总览](https://docs.openclaw.ai/automation/cron-vs-heartbeat)。
- 目标 build 证据：`.claude-plugin/types/` 由官方 2.1.289 生成（本轮只核 heartbeat/channel 相关 symbol）。
- 另补读 [channels-reference](https://code.claude.com/docs/en/channels-reference) 的相关小节：capability、content/meta 包装、无处理 ack、busy 批量交付、reply tool 与 permission relay 字段；未审完整示例实现。
- 引用但**未取到**：[goal](https://code.claude.com/docs/en/goal)、OpenClaw 的 `cron-jobs/*` 各 child 页、[automation/hooks](https://docs.openclaw.ai/automation/hooks)、[standing-orders](https://docs.openclaw.ai/automation/standing-orders)。
- 与既有主题接缝：scheduled wake 是 [context map](context-map.md) 中“动态 reminders / 生命周期”的一类来源；channel/task-notification 是 [continuity and memory](continuity-and-memory.md) 中“外部动作结果未知”的运行时对应物；Mods `session.receive/send` 事件细节见 [Mods migration](mods-migration.md)（本文不改该文件）。
- 版本与来源：[references/heartbeat-sources.json](../references/heartbeat-sources.json)。

## 未验证 / 缺口

- **本主题无实跑**：未建 cron/heartbeat、未联系 channel。另一个本地 slash-command probe 已运行 CC 并生成 2.1.289 声明；**声明可用不代表 scheduler/channel 实跑**。未安装、未动 VPS、未 commit/push。
- channel 的实际批量顺序、reply 和 permission relay 未实跑；官方使用通知方法 `notifications/claude/channel`，不虚构 `channels.push` API。
- OpenClaw：`cron-jobs` 只取到索引页；run lifecycle、retry、payload/session execution styles、webhook/Gmail 细节在未取 child 页，**未写**。
- 本机时区/环境对 CC jitter 与 OpenClaw activeHours 的实际表现未测。
- 目标 build 生成的 `session.receive` 分类与 2.1.277 公开声明有差异，已在正文标注；进一步以目标版本行为验证为准。
