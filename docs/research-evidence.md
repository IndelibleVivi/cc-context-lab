# 研究证据与覆盖记录

记录 2026-10-04/05、10/13 与 10/25 已读来源、测试条件和未验范围。观察日期不代表后来重新实测，文中的“本轮”按所属日期理解。本页保留可复核的研究依据；当前能力、状态与下一集成点以 [current state](current-state.md) 为准，技术主题仍归对应专题与 references。

## 2026-10-25：方向校准与验证覆盖

10/25 对初始 `cec2344`、现有技术专题、实验/Atlas/candidate 路径与历史纠正做了有界复核。目标是掌握 context 的来源、装配与生命周期，服务伴侣交互和受管 runtime 的持续演进；初始的完整 owned-context 不能收缩为 token 裁剪、局部提醒替换或工程 scheduler。研究曾长期留在 working tree，文档观察日期不代表对应 Git commit。当前能力结构与连续建设见 [development programme](development-programme.md)，[README 架构图](../README.md#架构与边界) 区分 Lab 的数据路径与原 owner 的接续权限。

已贯通 [可复现的 A/B context 研究](../experiments/companion-input/STUDIES.md)：固定完整合成 fixture snapshot、问题与保留要求，复用 canonical `run_session`，将逐来源轨迹与机会对照接入 CLI、Atlas 和固定的 brief 附件。研究可保存/恢复、CLI 重跑、按 snapshot 重开，并从来源检查完整输入。保存的是输入与配置，跨引擎代码版本不保证结果相同。typed decisions 仍为独立 shadow 实验，没有改变后续 ledger。

新 [请求观察与比较](request-observation.md) 提供 harness-neutral capture 合同和纯本地 CLI；Anthropic Messages / OpenAI Responses reader 保留 body、instructions/messages/tools、多模态块、参数 schema 与未知字段。Atlas 第六视图可选 A/B、看条件和 section 原值、搜索、展开完整 body、下载 canonical JSON/Markdown，并固定带入变更 brief。同格式只按 JSON pointer 对照，跨格式不自动配对；origin/lifecycle 保持 unknown，服务端历史/prompt 引用不展开。captured_request 是导入者声明，不等于独立 runtime 证明；当前验证仅使用合成 captures，不承诺使用这些 wire formats 的所有 harness 兼容。

已用反例修复 UI-only 环境与消息预览进入 current/history 的缺口，保持 archive 原文；Atlas 的错误导入、空问题导出、输入/输出 alias、软硬链及异常编码写入也有回归。两个报告 CLI 与 Atlas 共用先完整编码、预检、暂存后逐文件 atomic replace 的 writer；这不是多文件事务。请求观察的显示、搜索与下载使用 Python canonical 字符串，避免 JS Number 将 `9007199254740993` 舍入。真实 capture 仅显式导入 Git 外或 ignored 目录，默认页面只含四份合成示例；不自动发现 logs 或访问引用 URL。

本轮统一入口 `python3 scripts/check_offline.py` 已通过：companion 25 + schema 14 + decisions 33、study/CLI 13、Atlas 投影 7、study UI 8、candidate Node 14、checker 2、request preparation 4，以及 request observation/CLI 26、Atlas output safety 8、observation UI 5，共 **159 项顶层/Node case 计数**，另有三项 JS syntax。测试不调用 CC binary、第三方 checkout、网络或真实 provider。

浏览器已完成 study 的 download → CLI → builder `--study` → 恢复/重开 → 来源轨迹 → 完整回放 → brief；新观察页完成同格式/跨格式、原始 schema、搜索空结果/恢复、未展开引用、原值下载和固定附件后继续切换/移除。实际 JSON/Markdown 下载与 builder canonical 文本相等，brief 保留固定的原比较；另用显式两份大整数 capture 检查只导入指定文件、默认打开观察、精确原值显示与下载，CLI 与 Atlas 比较一致。1440×1100 与 390×844 六视图无页面横向溢出，窄屏观察条件/原值用单列；console 未见应用错误。README Mermaid 已在本地渲染核对，未加入 runtime dependency。以上来自 loopback 静态预览，不声称 file URL 或真实 harness 验收。本轮没有新的 CC 探针、模型推理、scheduler、消息发送、安装、VPS 或部署操作。

## 研究判断与技术边界

1. 研究持续伴侣交互中的 context 来源、装配与生命周期：当下状态、环境、自动召回、输入包装和自主轮次都在范围内。此前默认 harness 指导的替换研究继续保留，覆盖 system、tools、messages 与会话生命周期；本轮不继续提示词裁剪。
2. 官方主提示替换、来源开关和 Mods 是不同控制面。优先评估支持的结构化入口；二进制 patch 作为有具体覆盖缺口时的候选，不能预先一概采用或淘汰。
3. `session.compact` 的已读公开类型支持改 instructions、待摘要 messages，也允许不调用 `next` 直接返回压缩后整组 messages；这是自有 writer 的候选接入点，不证明目标版本已运行或覆盖全部内部摘要路径。详见 [Compact control](compact-control.md)。
4. 运行事实可以重新表达；来源正文必须保真。engine 生成的消息仍可能包含外部原文。
5. 新 repo 维护研究和实验；已有 runtime 的配置变更回到它自己的 renderer / runbook。本阶段只在本地工作，不动 VPS。
6. 此次读到的 tweakcc upstream 已在 native 路径调用 `applySystemPrompts`；fixed 关于 upstream 跳过 native 的宽泛比较不能继续引用。fixed 的默认摘要行为补丁也必须从 prompt 变化中分离，具体证据见 [upstreams](upstreams.md)。

7. 旧公开 types 仍标 2.1.277；本轮已用本地命令会话生成目标 **2.1.289** types，补核 prompt/tool/compact 等指定 symbols。`attachment.detail` 只声明三类 plan-mode 结构，不能外推所有 reminders；覆盖见 [target runtime](target-runtime.md)。初始 instructionFiles 与 nested loader 的差异仍见 [Mods migration](mods-migration.md)。
8. reminder 包的内容选择与 patcher 能力分开：正文没用到 removed/removed_names/tag_name，不代表其 placeholder 不可用；原函数合成链路已验证三者可用。
9. Forge / Swap / Carryover 与主提示、reminders 同属 context 生命周期研究；按操作定义，不能把 LMC-5 的 DB rollback 与自有 runtime 的 handoff 复用混为一谈。新专题见 [continuity and memory](continuity-and-memory.md)。
10. 自有 hook 的 `additionalContext` 也经 system reminder 进入请求；整类静音可能删掉续窗资料。官方长字符串 file/preview 边界已核，完整交付与语义使用仍需实测。

## 已建立的依据

- 已核对官方 CLI、environment variables、Agent SDK prompt guide、Mods reference/testing/troubleshooting、bare mode 与相关 changelog；入口和查阅范围见 [official controls](official-controls.md)。Mods HTML 页面在一次 web 读取中不可用，随后成功读取同站官方 `.md` 正文。
- 上游源码的 exact revisions、文件覆盖和限制集中在 [upstreams](upstreams.md) 与 [catalog](../references/upstreams.json)，不把可变 `main` 链接当作固定证据。
- 已完成本地受管 runtime 的有界 source 阅读，确认现有 hook 注入、marked transcript pruning、candidate renderer 和启动参数合同。私人机器映射保存在 Git 外，本页不把本机 source 当作 VPS 当前状态。
- 已整理三组完整配置对照、生命周期测试矩阵与结果记录格式；见 [experiments](../experiments/README.md)。
- `check_upstreams.py` 的合成验证已覆盖未变 / 有更新 / 查询失败，对应退出码 0 / 1 / 2。2026-10-04 扩至十一个来源后实查：七个 pin 一致，lobotomized、tweakcc-fixed、tweakcc、system-prompts 四个 branch tips 已前进；10/05 主线程已 fetch 这四个 tip（见 `.cache/profile-source-refs.json`），本轮对其增量做了与主 system/tools/compact 有关的有界 diff（见下与 [Prompt differences](prompt-differences.md)），但仍保留原已读 pins 与旧 fixtures 引用，未把新 tip 升格为完整已读 pin。此检查不读取或改变 CC 安装。
- 已对 roof-mod 原 handler 完成 F01/F02/F03/F04/F05a/F05b 六项合成复现及两项保真对照；另对 fixed 的原 placeholder/apply 函数完成 P01–P05 五组检查。没有运行安装器或文件系统 apply driver，不是官方 plugin test 或真实 CC 验收，见 [实验记录](../experiments/README.md)。
- 全部 41 份 lobotomized reminder 文件已逐项映射到 fixed 的 35 个 registry 条目和 6 个 per-server 文件；解析、内容保留、空正文及应用路径见 [Reminder overrides](reminder-overrides.md)。named system prompts 与 tool descriptions 已做确定性文件/正文对应（见下条），但仅对主 system 核心、常用工具与 compact 路径做语义深读，未逐份深读。
- 10/05 对 lobotomized tip `b867bb28`（作者标 CC 2.1.288）的 named prompt 目录做了确定性文件/正文对应，用**同版本基线** `tweakcc-fixed@6520e0cc data/prompts/prompts-2.1.288.json`：9,771 个 `.md` 中 exact 3,598、norm_only 5,128、changed 805、suppressed 202、unmatched 38（=作者拆分的 `inline-*`）；可对应 9,733。**文件数不是改写数**；exact 指 header 移除+strip 后与 joined pieces 相同（非原始文件逐字节），`norm_only`（占位符名/空白差异）不等于作者未改。作者 README 的 764 rewritten + 199 cut 是 2.1.280 口径的作者报告。可用 [compare_prompt_inventory.py](../scripts/compare_prompt_inventory.py) 复现（含 `--selftest`）；逐类依据与四 repo 增量见 [Prompt differences](prompt-differences.md) 与 [prompt-differences.json](../references/prompt-differences.json)。
- 10/05 形成第一份自有候选 profile（`cc-context-lab:v0`，未部署），唯一入口为直接导出的 `register(on)`，源码 Maps 在注册时取 snapshot。注册 `prompt.section`（默认选中 **0 个 engine section**）、`prompt.compose`（合成 core 作为 **session** section 去重后放 shared/session 边界）与 `tool.describe`（只改 engine/core Bash description）；未注册 attachment/context/compact。14/14 Node 合成 tests 通过；随后已取得一次本地 print/lean composition 观察，其他分支与正文分类仍未证。见 [Profile design](profile-design.md) 与 [candidate](../experiments/context-profile/README.md)。
- 已用官方 **Claude Code 2.1.289** portable artifact 实跑 strict validator 和 test kit：**校验通过，3/3 官方 tests 通过**。原 factory 导出曾被官方分析器拒绝，改成直接导出函数后通过；官方 loader 在测试进程中实际加载了 module，engine 答案为合成 stubs。没有安装或启用模型会话。新的 [升级检查入口](maintenance.md#检查指定-cc-版本的-candidate) 为每次 run 保留干净副本、独立 config、版本和分层报告，不能把空 suite、不支持命令或未知输出记成通过；脚本回归 2 项 unittest / 11 个场景通过。便携证据见 [compatibility record](../references/context-profile-compatibility.json)。
- offline 命令本身未生成 types；后续独立的 [本地命令探针](target-runtime.md) **已生成 2.1.289 的三份声明**，并观察 23 个 section 事件与包含 `lab:core` 的 9 段 composition。使用独立 config、合成 key、本机拒绝端点，实际收到 0 个端点请求；没有真实 provider/model 调用。model/promptModel 的本地选择为 `claude-opus-5-5`，traits `lean/print/skills`；只保存元数据。目标 types 不再列为整体未取得，已读 symbols 与未验分支分别记录。
- 已按官方 repo exact revision 重读 agents-md 主注册路径及 loader 差异，nested CLAUDE.md 的覆盖线索从“旧讨论待复查”推进到“当前公开 source/doc 已核”，仍不是目标 build 运行证明。
- 已将 Forge/Carryover 公开源码与现有自有 continuity 的职责区分。现有 controller/adapter 的有界本地回归共 59 项通过（Core 34、CC 25）；使用合成事件和临时目录，没有 provider 请求或生产操作，source 定位与详细证据留在 Git 外。
- Pi 的原生投影、Cliff 的 proxy 前缀与重复压缩策略、Claude API context editing/compaction 已做文档层对照；未安装、运行或审计这些实现全链路。exact revisions 与阅读边界见 [catalog](../references/upstreams.json) 和新专题。
- [八组 continuity 语料](../experiments/continuity-cases.json) 已建立，覆盖范围、指代、较新纠正、来源继承、时间、附件、未完动作与 manager 组合；尚未运行模型语义比较。
- 已对 LMC-5 `fb3e72c9` 原函数复现九项选择/截断/预算观察，包括同一句工程决策仅加关键词即改变选择、中间限定丢失、tail 超目标预算；详见 [Forge upstreams](forge-upstreams.md)。教程的完整扩展未在所查路径找到，但公共 extras 确有启动包 builder 与冷仓 recall adapter，不能写成“上游没有冷仓”。
- 10/05 新核官方 compact 合同：classic PreCompact 可阻断，PostCompact 不能改结果，SessionStart 的 `compact` source 可重注入；内置 `/compact` 不经 Skill 工具调用。局部 summarize 与 Mods 事件的对应仍未验证。重载来源、技能预算、`handle` 与 subagent loop 边界集中在 [Compact control](compact-control.md)。
- 两份指定 Markdown reference 已按目录完整重读，详细覆盖与出处留在 Git 外；可复用归纳补入 continuity 主题，并形成 [handoff / curation 候选正文](../experiments/handoff-policy.md) 与合成例子。它们没有安装为 Skill，也没有替换既有生产 handoff schema。

## 线程状态、心跳与保留策略

2026-10-05 范围已明确为**伴侣交互中的 context**，不限于工程调度或系统提示裁剪：包含自主轮次、ambient/present state、时间/天气/location hooks、channel/终端包的输入头尾、非主模型主动调用的记忆召回，以及保留/续窗。入口为 [Companion context](companion-context.md)；[context map](context-map.md) 连接来源、装配和生命周期。研究不启用 scheduler、不发送消息，也不迁移外部 Memory/state backend 的职责。

已找回并读完先前的心跳 report 与后续研究建议；那轮没有部署，旧建议不构成本轮实现指令。早期 Atrium source gate 与更晚重做建议分开；旧 wake/Contact 设计不自动成为当前基线。Atria State 只读了当前 source contract 的 fresh attention 与 retained review 边界，未读取 live state。私人材料出处与阅读范围留 Git 外。

[Heartbeat / channels](heartbeat-and-channels.md) 保留为实现机制对照：官方 CC/OpenClaw 的 tick、turn、内部结果与外部交付分开；CC `durable` 注释与当前 resume 文档存在须实测的差异，未强行合并成一个结论。新补读 Mods timer/submit，以及目标 `PromptSubmitInput.context` 的原话后附加通路；仍是声明/文档证据，没有运行 timer、自动召回或 channel。

[公开实现对照](companion-source-dossiers.md) 已按 exact revisions 完成六项有界阅读：Siigari 的 Stop/inbox/supervisor、Hindsight 的模型前召回、memsearch 的开场日志与用户可见能力提示（`systemMessage` 不等于模型 context）、roof-mod 的既有 context 转换、CcCompanion 的独立 API 教程、Dylan 的唤醒时天气与历史包装。后两者不是原生 CC hook；作者意图与源码执行顺序分开记录，例如 Siigari backlog 可共享 session、Dylan 写回只构成一次 gateway POST 尝试。此六项没有运行验证。五个新增来源已接入原有只读 refs checker，总 catalog 为十六项；新增五项 refs 本轮实查均与已读 pin 一致，旧 pins 未自动升级。

“阅后即焚”历史教程已完整读完，原函数对临时合成 transcript 的 **8 项观察复现**：含清除所有已存在匹配条目、混合数组载荷损失、sentinel 读取失败会启用、写后异常不自动回滚。官方当前 hooks 并行合同也否定仅靠 settings 顺序保证“先清理后注入”的前提。这些发现尚未应用到生产 source；活跃进程/下一次 request 效果未测。

[心跳跳法](heartbeat-patterns.md) 与 [离线输入包实验](../experiments/companion-input/README.md) 已建立：触发来源、执行目标、历史方式分别记录，明确 `turn_busy ≠ chat_active`。六种 trigger × same/fresh，加 fixed/hybrid 的三种 placement 对照；**24 项 checks 通过**，两段合成情境的完整 JSON/Markdown 已生成。主聊天活跃时 main 自主候选跳过或延后，independent 只写自己的 ledger；取消按合并成员在 actual start 复查，内部结果不能提前进入本轮输入，fresh carryover 与只读主聊天快照均按可用性选择。此结果只验证 lab 假设，不是 CC scheduler、真实模型或交付验收。

10/05 另核 CC scheduled-tasks 的 idle/missed-fire 合同与 OpenClaw heartbeat 的 session/isolatedSession/target 和 busy guards；独立 context 不自动代表可以并行。Dylan 的最近 user 时间阈值也不等于主聊天活跃锁。具体来源和阅读范围见上述专题及 references；没有启用任何实现。

10/13 新增 [Heartbeat decisions](heartbeat-decisions.md)：研究 Clef / Decisions API 式 typed decision 对自主轮次的用途。已读已有 Decisions Lab 的任务、集成与评估合同及相关 adapter source，并核对当日 Cloudflare Clef-Flash 与 OpenAI Decisions 官方接口；来源与覆盖见 [record](../references/heartbeat-decisions.json)。心跳任务采用五个有限选项；placement、聊天占用、取消与历史归属仍由明确规则拥有，不以模型判断或 confidence 覆盖。模型推理与真实心跳接入尚未执行。

10/13 [决策离线实验](../experiments/companion-input/DECISIONS.md) 已跑通：**21 个 scripted cases、0 项期望违例、8 个去重任务**；分别生成 Clef-Flash 和 OpenAI Decisions 的 8 条 `PREPARED_NOT_SENT` 原生请求正文。统一 lab checks **71 项通过**（原输入包 24、答案合同 14、决策/入口 33），请求导出器另 **4 项通过**。覆盖回答身份绑定、开始之后发生的过期/纠正/取消、合并成员退出、未变化的迟到回答、历史正文保留、纯 prepare 不消费答案，以及 check 失败退出。原 `run_session.py` 未替换；新选择只作为 shadow 注记，不重算后续 ledger。真实 provider response adapter 未接入，模型评估仍 `NOT_RUN`。


## Context Atlas 与运维准备

10/05 已将现有研究接成 [Context Atlas](../workbench/README.md)：12 个 context 环节的关系/证据图、两种情境下全部 6 trigger × 3 placement × 2 history（共 **72 个组合**）的合成回放、可导出的变更 brief，以及十六项上游的来源检索。builder 直接复用 companion-input 引擎；没有第二套调度模拟器。HTML 内嵌数据和样式，不需要 CDN 或 provider。

[Context DevOps](context-devops.md) 贯通 CC 升级、输入调整、自主活动、窗口生命周期四种完整操作。证据绑定 build、启动入口/模式、candidate、context 来源与 session 路径；单个版本的 offline 通过不代表整套配置兼容。Atlas 的关系和检查映射由研究者维护，并非自动扫描的生产依赖。原 runtime 继续拥有 renderer、selector、激活与恢复。

10/05 构建与 **4 项投影检查**、JS syntax 通过；headless Chromium 实际走过 72 个回放组合、主聊天跳过/延后/独立 session 的差异、preset 替换与自定义选择、Markdown 下载、来源搜索/空结果/恢复、键盘 tab 导航。1440×1000 与 390×844 页面已检查，窄屏四个视图无页面横向溢出（来源表内部可横向滚动）。浏览器验证经 loopback 静态预览；不将其记为直接 file URL 的浏览器验收。当时未启用真实心跳、模型、消息交付或生产配置；此段保留 10/05 的原观察条件，当前 source 状态见页首。

## 仍未验证

- 新通用观察器对实际 harness capture 的使用与 runtime provenance 核验；当前 reader/CLI/Atlas 只有本轮合成输入验收。缺少来源身份、服务端历史与模型使用证据时仍保留 unknown / 未验证。
- typed heartbeat decision 的真实推理、语义增益、usage/延迟和 provider 截断行为；scripted replay 不能替代模型评测，shadow 注记不证明决策改变了后续历史。Decisions Lab 的 next-action collector 也未直接接到本题。
- 真实环境如何判定整段聊天结束，以及心跳、自主活动、ambient/环境 hooks、自动召回与输入头尾的目标 CC 真实请求及自然使用效果；公开 repo 的 bounded source reading 不等于适配或部署。
- 日常本机或 VPS 安装版本、真实模型会话的 Mods 开关和加载状态；目标声明除已列 symbols 以外的内容未审。已检查的 2.1.289 是独立 cache artifact，不代表日常安装。
- 新会话 / compact / resume / subagent 的真实 request bodies，以及实验三组的行为差异。
- 各 patch 工具对目标安装方式与版本的兼容性、非提示副作用、升级和恢复结果。
- 修改落盘 transcript 对正在运行进程的真实输入影响。
- 自有 Forge fork 的真实有效工具池、目标 CLI inline 交付、下一轮语义连续性；现有长度/覆盖拒绝对实际使用的影响。
- 多轮压缩的事实来源继承、关系/工程混合事件的保真质量，以及多 manager 的最终请求和缓存代价；目前只有研究合同与合成语料。
- 其他独立归档教程与云盘备份正文仍未完整重读；本轮已读的两份 Markdown 不代表其配套 writer、注入脚本或 taxonomy 附件已经核实。

以上是后续研究问题；不妨碍本研究库已可使用，也不构成运行时方案已完成的声明。

## 未完成研究的具体接点（2026-10-25）

当前已有整套离线研究、可复现 A/B、本地请求观察与带结果的变更准备路径；后续以 [四种完整运维问题](context-devops.md) 和 [连续 programme](development-programme.md) 组织证据补齐。下一主线是沿已经可用的 capture 入口，把同一研究问题、条件和保留要求连接指定 build/入口/candidate 的实际观察，再交回原 runtime 的接入与自然使用；不另起第二套调度器，也不把新增 UI 当终点。自主活动这条链可沿公开实现核“谁触发、在哪里活动、如何判断聊天占用、结果何时交回”，把源码可证的边界与 lab 假设对应起来；真实请求或自然行为实验需相应授权。伴侣 context 的其它供给方式仍可继续比较：常驻与独立自主轮次、按轮/按变化/事件式环境输入、开场与每轮自动召回、channel/bridge 包装，以及旧内容退出条件；来源见 [Companion source dossiers](companion-source-dossiers.md)。本轮不继续剪系统提示词。下面主提示与 compact 的既有研究线保留，不能因扩展主题而丢失，也不在未获新授权时启动生产接入。

两条研究线按来源与生命周期衔接：主 system/tools 已对 tip 的 9,771 份 named 文件做完确定性文件名/正文对应（exact / norm_only / changed / suppressed / unmatched），但 changed 内的实质改写与 38 个 `inline-*` 仍未逐份语义深读；continuity 先用已建立的语料核“默认 reminder 变换是否误删自有 bridge”和“历史投影是否保留中间纠正”。复用现有 controller/adapter 作为接入基线，不在研究 repo 重建生产配置或 Memory DB。compact utility prompts、普通/fork subagent 保留独立路径。

compact 的后续实现候选是在官方事件里接入自有 writer，并独立核压缩后重载；暂不因为能返回 messages 就放弃现有 Forge 的 fresh-session/recovery 职责。两份写作草案先与已有六字段 handoff 对照，再在获授权的隔离环境检验真实输入和语义，不直接复制第三方写入命令。

四项新 tip 已做本轮相关范围的增量阅读与目录对照；未读部分保留在 [Prompt differences](prompt-differences.md) 的覆盖限制中。现已取得目标 build 的一次 section 映射，下一步补其它分支与动态事件证据，不重复把已完成的 bounded diff 当待办，也不把它升级为全仓审阅。

今后版本迭代先用同一升级检查脚本调用所选 binary，保留各版本官方 offline 结果；这条路径已跑通，不重复作为待办。目标 types 与一次本地 composition 探针也已完成；下一层缺口是其它分支的正文分类、动态事件以及请求生命周期，需要真实请求证据时再安排获授权的隔离模型实验。现有 reminder 映射、原函数 fixture 与 continuity source tests 都不代表整个生命周期验收完成。

GitHub 远端已建立为 [IndelibleVivi/cc-context-lab](https://github.com/IndelibleVivi/cc-context-lab)，visibility 已核为 private，研究内容由 `main` 管理。没有公开发布、安装插件或部署；远端 refs 不代表任何 CC runtime 已更新。私人材料与上游缓存不进入远端。
