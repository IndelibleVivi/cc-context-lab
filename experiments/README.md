# 实验设计与证据

当前包含 roof handler 合成复现与保真对照、reminder placeholder 链路、Carryover 选择实验，自有 context-profile 的 Node/官方 offline 测试，以及心跳输入包的离线设计比较；真实模型和真实 scheduler 的生命周期比较仍是待执行设计。上游源码阅读不算实验通过，已有讨论中的测试叙述也不算本 repo 的新结果。

针对一次具体 context 改动，使用 [可复现 A/B 研究](companion-input/STUDIES.md)：固定完整合成 fixture、研究问题与 A/B 配置，经同一个引擎生成逐来源轨迹与机会对照；CLI 输出 JSON/Markdown，Atlas 提供检查、保存/恢复和带结果的 brief。它连接已有实验与变更准备，不替代真实 request 或模型语义实验。

[请求观察的四份 synthetic fixtures](request-observation/fixtures/) 对照两种 wire format 下的 instructions、tool schema、tool outputs、cache 与未知字段。使用 [inspect_context.py](../scripts/inspect_context.py) 检查/比较；这些是人为构造的本地材料，不是本 repo 新捕获的实际请求。通用观察接口与私人捕获边界见 [request observation](../docs/request-observation.md)。

## 首份离线复现：roof-mod 的边界

2026-10-03，对 `kagamiurayama/claude-code-roof-mod@888dceb88631186dfcf01d69b088bedec9c1009a` 使用 [roof-boundaries.mjs](roof-boundaries.mjs)，直接调用原 module 注册出的 handler，stub `next` 为原样回传。本轮运行使用 Node.js v26.7.0。全部输入为合成材料，无模型、网络、CC 进程或用户配置。

```sh
node experiments/roof-boundaries.mjs .cache/upstream-sources/kagamiurayama--claude-code-roof-mod
```

先取得并阅读该 exact revision 的本地 checkout；`.cache/` 不随 repo 分发。脚本会执行该 module，请勿指向未经阅读的不同源码。测试中的 preamble 从源文件读取，不在本 repo 复制原厂长提示。

实际输出：

- F01：带插件命名空间的 section 内，身份句的代码块引用被改写；id/scope 并未限制改写。
- F02：CLAUDE.md 引用内 preamble 被删除。
- F03：构造的非 engine 同类型事件被静音。
- F04：channel guard 文本保留，同段 preamble 仍被删除。
- F05a/F05b：todo_reminder 的合成任务事实、bash_output_audience_note 的合成交付约束随整条 text 一起丢弃，未传给 next。
- 两项对照：未在静音名单内的 hook 原文、无匹配目标句的 section 均完整保留。

脚本以这些行为成功复现为退出 0 的条件，**退出 0 不表示插件满足保真合同**。F01/F02 是已知目标句在合成引文中的反例；F03/F05 的来源/类型/正文组合是实验构造，未证明 CC 真实发出该组合，也不声称某次真实任务已经丢失。

此复现未使用官方 `claude plugin test`，不证明真实 Mods API schema、加载、最终 request 或模型行为；后续采用时仍需目标 build 的事件类型与真实路径验收。

## Reminder placeholder 的原函数链路

2026-10-03，使用 [reminder-placeholders.mjs](reminder-placeholders.mjs) 对 `skrabe/tweakcc-fixed@f3cf2d9978e209cea1383a0262fa5fc7089aea50` 做合成 bundle 检查，运行环境 Node.js v26.7.0：

```sh
node experiments/reminder-placeholders.mjs .cache/upstream-sources/skrabe--tweakcc-fixed
```

脚本从已读 checkout 提取 `substitutePlaceholders`、`escapeNonAscii`、匹配 helpers 与四个选定 registry 对象，用 Node 的 `stripTypeScriptTypes` 去类型后在 VM 中调用；`showDiff` 是空 stub。它执行原函数处理合成字符串，不导入整个上游包、不运行文件系统 apply driver、不读写 CC 安装，也不发模型请求。Node 对 stripTypeScriptTypes 的 experimental warning 不影响这次结果；未验证其他 Node 版本。

五组实际通过的检查：

| ID | 输入与判据 | 已证范围 |
| --- | --- | --- |
| P01 | 在自定义正文使用带空白的 `{{ removed }}`，模拟移除一个 agent | whitelist 展开与通用 `${H.` 变量重绑定可端到端输出被移除名称 |
| P02 | 自定义正文使用 `{{removed_names}}`，模拟移除一个 MCP server | 占位符可用；包里没使用它与工具不支持是两回事 |
| P03 | `{{tag_name}}` + 合成 local-command-caveat wrapper | 正确绑定实际 tag 变量 |
| P04 | `$` 前缀加 `{{used}}` / total / remaining | 最终输出为 `$5/$10; $5 remaining`，没有额外货币符号 |
| P05 | 中文、反引号、反斜线、字面 `${untrusted}`；另传未知 placeholder | 普通文本保真；未知 token 返回 error 并不给出 substituted body |

测试由初稿的具体误判触发：它把 body 未用到的 placeholder 误判为 apply 没接线。原函数的合成结果反驳该判断，逐项表据此修正。这些 fixture 只覆盖构造出的 code shape 与选中路径，不证明任一 CC binary 的 anchor 命中、安装兼容性、全部 registry、恢复或运行效果。

## Carryover 原函数选择实验

2026-10-04 对 LMC-5 `fb3e72c9` 的原模块执行 [carryover-selection.py](carryover-selection.py)，在 Python 3.9.6 / 3.13.3 下九项观察全部复现：头尾截断丢中间限制、关键词改变同一决策的选择、整条超长排除、wrapper 字符串排除、合成 sentinel、poison 词计数，以及保留 tail 导致超出 token target；另含原文保真 control。完整分组与限制见 [Forge upstreams](../docs/forge-upstreams.md)。

```sh
python3 experiments/carryover-selection.py .cache/forge-public/wuxuyun0606-collab--lmc-5
```

使用上述固定 source 的本地 checkout；脚本直接加载它，不是任意未审 Python 文件的安全 sandbox。没有运行上游 session 写入或 `--resume`。成功退出证明观察复现，**不是算法达到保真或生产验收**。

## context-profile 候选（未安装 source）

2026-10-05，[experiments/context-profile](context-profile/README.md) 提供第一份自有 profile 的离线 candidate：一个**未安装、未在模型会话启用**的 hooks module。直接导出的 `register(on)` 读取源码 `sectionOverrides`/`toolDescriptionOverrides` Maps，默认选中 0 个 engine section，外加合成 core 与 14 项 Node 内置测试。用合成 `on`/`next` 链验证：显式 section 改写/`text:null` 保留/未选中保真、engine-tier tool description 改写（core 实际收到的 event 除 description 外不变）、自有 core 作为 **session** section 去重后放 shared/session 边界、attachment（未注册）三种 origin 基线保真。合成 core 只是公共例子，不是最终身份；test 的 `lab:synthetic-guidance` 是合成 selector。

```sh
node --test experiments/context-profile/tests/register.test.js
```

本轮实跑：14/14 PASS（Node v26.7.0）。另通过 [check_context_profile.py](../scripts/check_context_profile.py) 调用官方 **Claude Code 2.1.289**：strict validator 通过，`tests/official.test.ts` 的 **3/3** test kit 检查通过。这一层实际加载 module，engine 答案为 synthetic stubs；原 factory 导出曾被官方分析器拒绝，现只有直接导出的注册路径。完整命令、退出语义和记录方式见 [maintenance](../docs/maintenance.md#检查指定-cc-版本的-candidate)。

目标 types 未由这两条命令生成；后续独立的本地命令探针已生成 2.1.289 声明（见下）。真实 HTTP request、模型行为与会话生命周期未测。`prompt.attachment`、`prompt.context` 与 `session.compact` 未接入。检查脚本另有 2 项 Python unittest（10 种 CLI 结果分支 + executable 缺失），验证退出码、干净副本和环境隔离。

## 目标 build 的本地 composition 探针

2026-10-05 使用 [probe_context_runtime.py](../scripts/probe_context_runtime.py) 启动隔离的本地 slash-command 会话，官方 2.1.289 生成三份类型文件，实际触发 23 个 section 事件；composition 中的 `lab:core` 位于 shared/session 边界。模型端点为 loopback 拒绝服务，本次收到 0 个请求。所有 metadata/类型/config 留本地 cache，便携结果见 [target runtime](../docs/target-runtime.md)。这与官方 test kit 的 engine stubs 分开，也不是模型请求或 compact 验收。

```sh
python3 scripts/probe_context_runtime.py --claude '<trusted-claude-executable>'
```

## “阅后即焚”的原函数观察

[burn-after-reading.py](burn-after-reading.py) 对已审阅教程的 Python code fence 做 8 项原函数复现，全部用临时合成 JSONL；B01–B08、来源限制与反例解释见 [Context retention](../docs/context-retention.md)。退出 0 代表观察复现，不代表算法可用于活跃 CC 或已省下 tokens。没有复制教程实现、修改原件或操作真实 transcript。

```sh
python3 experiments/burn-after-reading.py '<reviewed-tutorial-file>'
```

心跳、定时、channel 与清理组合的语义判据见 [Heartbeat / channels](../docs/heartbeat-and-channels.md) 和 [Context retention](../docs/context-retention.md)；未启动任何真实 scheduler、channel 或长驻进程。

## 心跳与 companion 输入包的离线比较

[companion-input](companion-input/README.md) 用同一条完全合成的时间线，比较固定间隔、扰动间隔、事件、自约时间、空闲窗口、混合六种候选规则；再单独切换执行会话自己的历史与 fresh 有界承接，并对 fixed/hybrid 比较主聊天跳过、聊天结束后执行和独立 session 三种放置。`turn_busy` 与 `chat_active` 显式分开。假设输入包记录触发原因、忙碌后实际开始时刻、来源版本与时效、原话/包装、自动供给的记忆、历史及预写结果。

这是原创规则的可执行设计比较，不是上游原函数复现或 CC/OpenClaw 行为测试。所有自主选择与结果都是 fixture 预写数据；无 LLM、真实天气、channel、CC 进程或 scheduler 服务。生成输出留在被忽略的 `.cache/`，命令、规则和已跑结果以实验目录 README 为准。设计选择和其它跳法见 [Heartbeat patterns](../docs/heartbeat-patterns.md)。

## Typed heartbeat decisions

自主轮次的 typed decision 另见 [DECISIONS.md](companion-input/DECISIONS.md)：复用上述引擎的准入与 packet，准备 `heartbeat_activity` 任务并回放合成回答。五个业务选项、规则 baseline、unknown/refusal/error 与迟到状态复查分别记录；不把答案选择当发送或重新排期，不把 scripted replay 当模型质量证据。机制与 API 依据见 [Heartbeat decisions](../docs/heartbeat-decisions.md)。


## 默认指导的离线检查矩阵

| ID | 合成场景 | 应观察的结果 |
| --- | --- | --- |
| F01 | 插件 section 的代码块引用包含身份模板句 | 期望原文保真；已复现全局改写 |
| F02 | 指令文件代码块引用旧模板开场白 | 期望保真；已在上述 snapshot 复现缺陷 |
| F03 | 相同 reminder type，来源不同 | 期望先按来源判断；已在构造输入下复现缺陷 |
| F04 | 外部 channel / quoted context | 期望所有阶段同范围保护；已复现缺陷 |
| F05 | reminder 带任务、工具输出或错误动态值 | 两项合成载荷已证明整条静音会一并删除事实；真实事件载荷未验证 |
| F06 | marked hook attachment + 普通消息 + 未标记 attachment | 只修改约定对象；UUID/parent 链条与原件可恢复 |
| F07 | Mods module 缺失、被跳过或规则未命中 | 不把 session 存活或一个 load marker 当作规则成功 |

fixture 必须由此 repo 新写，或在明确来源和许可范围内采用；不导入真实对话、账户或私人配置。官方测试入口见 [Mods testing](https://code.claude.com/docs/en/plugins/mods/test)。选定实现后再写匹配其真实合同的 tests，避免对尚不存在的 parser 编造 API。

## 再比较完整生命周期

以下对 [A/B/C 三组](../docs/profile-design.md) 都适用：

| 场景 | 检查 system / tools / messages 的什么 | 行为观察 |
| --- | --- | --- |
| 新会话 | 默认 sections、自己的 core、初始 instruction/context | 身份与任务理解 |
| Read / nested instruction / `@文件` | 后续插入位置、原文、文件状态事实 | 引用和文件使用准确 |
| Skill | discovery、skill 正文及额外指导 | 相同方法是否实际执行 |
| Bash / MCP / 后台任务 | 工具描述、server instructions、结果与提醒 | 可用性、失败解释、可见交付 |
| 普通与 fork subagent | 两种分支各自的 prompt 与历史 | 继承边界、交付质量 |
| 全量/局部 compact | 摘要请求来源、模板和进入下一阶段的摘要 | 承诺、未完成事项与表达连续性 |
| resume / continue | system snapshot、旧 reminders、重放事实 | 旧配置残留和新配置生效时点 |
| 旧 hook context 清理 | 磁盘记录与下一个实际 request 是否一致 | 不把文件编辑当作历史重建成功 |
| Forge / Swap / carryover | 原始 cutoff 覆盖、handoff 与 tail、hook 是否文件化、最终投影 | 指代、纠正、关闭事项、未完成动作与来源继承 |

同一模型、同一任务、同一 skill、尽量一致的工具能力；记录运行模式、prompt caching 和 snapshot 差异。至少包含一个真正需要探索的合成问题和一个能验证工具结果交付的任务，不能只测问候。

## 续窗的语义测试语料（尚未执行）

[continuity-cases.json](continuity-cases.json) 是八组原创合成输入与判据：范围和指代、中间纠正、继承不等于确认、关闭/未完成动作、附件与工具、跨午夜时间、未完论证与氛围，以及 reminder/历史变换的组合。没有真实对话或模型响应。

五种策略比较 pure tail、summary+tail、规则 Carryover、Memory+bridge、self-handoff+whole-turn tail。与本页 A/B/C profile 轴分开控制，避免同时更换 prompt、模型和历史策略后无法解释结果。先检查结构和实际 request，再评价下一轮行为；多次继承与反向草案也要保留来源。

JSON 的语法与字段检查只证明语料可读取；目前没有 runner 或模型调用结果。费用、cache、摘要调用、延迟、额外检索与恢复结果都在记录字段内。真实执行需要对应模型实验授权。

## 真实请求实验的准备

[Handoff policy](handoff-policy.md) 提供两份可供后续比较的原创写作正文，以及同一合成事件在 handoff、项目记录与长期 Memory 中的不同投影。它们不是可安装 Skill 或生产 schema，没有执行模型评估。沿用上述八组语料，补充原话不可见、未命名事件、一次性事实的置信与跨午夜歧义等审阅判据。官方 compact 接口的能力与限制见 [Compact control](../docs/compact-control.md)。

未来获授权后，在隔离安装/目录中使用合成任务，记录 CC version、安装方式、profile revision、Mods 加载结果及 request 来源。官方 raw-body file mode 是观察候选；先确认目标 build 的 telemetry 和 exporter 条件，输出保存在 Git 外，并检查没有意外的外部 exporter。[官方 monitoring](https://code.claude.com/docs/en/monitoring-usage#api-request-body-event)

`cchistory` / trace 类方案可能实际发模型请求；binary patch、清理 transcript、重启 runtime 也有独立副作用。当前研究不运行它们。不能把不支持某个事件的探针输出或模型自述用作“已经没有默认指导”的唯一证据。

## 结果怎么写

每个已执行实验留下简短 record：问题、profile/版本/上游 revision、合成输入、预期、实际、未覆盖范围、可复现步骤，以及是否采纳。具体失败必须保留；不把没有运行写成通过。

原始请求与私人工作记录留在 Git 外。Repo 只保留足以复现结论的合成 fixture、脱敏事实和自己的归纳。离线结果、真实 request、运行行为和 owner acceptance 分别标注。
