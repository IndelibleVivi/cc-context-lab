# 从 context 研究到受管 runtime 的变更

本仓库要持续服务实际的 context 运维：理解一个版本/配置的输入，比较替代机制，知道改动会波及哪里，并把有证据的变更交给原 runtime 项目接入。伴侣相处的当下感、自主时间与连续性是实际需求；工程手段要能够保留和解释这些行为。

范围已扩展到跨 harness 的 context engineering。CC 的具体控制面仍保留为独立研究线；共通的 [请求观察](request-observation.md) 开始接住 Anthropic Messages / OpenAI Responses 的显式本地材料。它比较输入原值和版本/入口条件，不推断 block 来源、隐藏历史或模型行为，也不把格式读取扩展成所有 harness 的兼容承诺。

研究成果因此需要连成整体：**来源与事实 → 输入装配 → session 生命周期 → 自主活动与外部交付 → 配置变更与观察**。不以单个 fixture 或一个新工具的存在代替整条链路。

[Context Atlas](../workbench/README.md) 是这些材料的本地交互研究入口。它把 canonical references、机制关系和同一引擎的合成回放组合起来；对照研究固定同一材料的 A/B，逐来源查看 current/history/excluded/轮后产生，能保存、重跑并把实际观察带入变更 brief。图表示研究关系，不表示已部署的服务架构。现有专题继续拥有技术结论，原 runtime 的 renderer/runbook 继续拥有配置和接入。愿景与阶段连接见 [development programme](development-programme.md)。

## 一个持续可用的研究对象

比较机制时，至少让读者找到以下事实；这是一套阅读关系，不强制另建生产数据库：

| 对象 | 要回答的实际问题 | 现有真源 |
| --- | --- | --- |
| 来源与版本 | 这份规则、正文或类型来自哪一个 revision / build？ | `references/` 与对应 source dossier |
| 输入位置 | 进入 system、tools、messages、history 还是只在 UI？ | [Context map](context-map.md)、目标 types 与 request 证据 |
| 活动位置 | 是谁触发，在哪个 session 真正开始，延续谁的历史？ | [心跳跳法](heartbeat-patterns.md)、[输入包实验](../experiments/companion-input/README.md) |
| 时间与有效期 | 何时观察、何时提交、此刻是否有效、旧内容仍在哪里？ | [Companion context](companion-context.md)、[保留策略](context-retention.md) |
| 继承与恢复 | compact/resume/Forge 后哪些被复制、重算、重载或退出？ | [Compact control](compact-control.md)、[Continuity](continuity-and-memory.md) |
| 交付与结果 | 内部发生过什么，哪段到达模型，哪条消息真的发送，哪个状态仍未知？ | [Heartbeat / channels](heartbeat-and-channels.md)、原 runtime receipts |
| 改动与验证 | 选了哪些入口，受影响的行为有哪些，下一层证据是什么？ | [Atlas 的关系模型](../workbench/model.json)、[Maintenance](maintenance.md) |

同一个对象可以有多层证据。“源码中存在一个 hook”“本地 loader 执行成功”“本轮真正收到正文”“下一轮正确使用正文”是不同事实。Atlas 展示各自的结论和边界，不把它们加成一个健康分数。

## 四种完整的运维问题

### CC 升级：理解差异，而后更换运行版本

从一个已知 build 与 candidate 出发，先定位相关官方接口/上游 source 的变化，再使用同一离线检查入口比较版本。已知 **2.1.289** 的 strict/test kit 证据和独立 composition 观察可以作为这一候选的研究基线；**2.1.277** 的公开类型只是另一份来源，不能与它拼成“中间所有版本兼容”。

一次证据应能定位到 **CC build + 启动入口/模式 + candidate revision + context 来源 + session 路径**。例如 print/lean、tools/MCP 关闭的一次 composition，不覆盖日常交互窗口，也不覆盖 resume、compact 或独立自主 session。版本是比较条件之一，不能独自承载整套配置的通过结论。

需要交给 runtime owner 的结果是一份具体差异：受影响的 sections/tools/hooks、载入与类型检查结果、仍需验证的 request 分支、是否影响 compact/resume/subagent，以及原有恢复方法还能覆盖什么。新版本号本身不提供通过证据。

维护命令、返回码、失败处理和原始报告位置由 [Maintenance](maintenance.md) 管理。Atlas 只整理相关命令与问题，不执行 binary、改 pin 或自动升级。

### 改输入：沿来源和生命周期追踪影响

例如，希望减少默认任务提醒，同时保留自己提供的当下状态和续窗材料。真正需要比较的是：改变了哪些 engine 模板，哪些应用事实由自有 composer 接管，哪些来源原文必须保真，哪些旧注入还留在历史。

这会同时关联 reminders、hook additionalContext、自动 recall、SessionStart 重载和历史保留。只观察“当前新包里没出现”无法判断旧历史是否仍在下一次 request 内。变更 brief 应明确本轮修改的入口、完整保留的材料，以及对下一次输入的可观察预期。

### 改自主活动：给自己的时间以明确位置

先分别选择触发方式、执行 session、历史方式与对外交付。固定/扰动/事件/自约时间可以组合；“外部触发”不能代替“独立 session”，“独立 context”也不能推定平台允许并发。

当前聊天的 turn 间隙仍可能属于同一段活跃对话。lab 明确比较 main_skip / main_defer / independent；真实实现需要核它依据的是当前请求、最后用户消息时间、队列状态还是另一种信号。内部活动可以安静结束，是否联系、何时把自己的经历交回共同聊天，须有单独的行为依据。

运维目标还包含计划取消、进程重启与重复交付：哪个 owner 保留未完计划，取消后合并队列是否仍会触发，外部结果 unknown 时怎样避免把尝试算成成功。这些问题留在真实实现的验收中；合成回放不提供运行时保证。

### 改窗口生命周期：保持可承接的经历

compact 的 writer、resume 的保存状态、Forge 的换 session/controller 与 Memory curation 各自处理不同对象。它们可以融合，但必须先确定谁拥有原事件、谁生成交接、谁负责旧窗口停止与恢复。

一份可接入的方案需要从旧窗到下一轮讲清楚：选入什么、原话在哪里、较新纠正如何生效、未完动作如何承接、什么资料在开场重新加载、失败停在哪一层。继承摘要保留来源，并不生成新授权。[Handoff policy](../experiments/handoff-policy.md) 提供写作候选；现有八组语料仍需真实语义实验，不能用格式正确替代相处的连续性。

## 工作如何交回原 runtime

| 阶段 | Lab 能交付什么 | 下一位 owner 要持有的事实 |
| --- | --- | --- |
| 定位 | 明确版本、入口、source pin 与问题 | 目标 runtime 当前真源与选中的配置 |
| 比较 | 机制差异、合成输入/历史回放、来源保真结果 | 要改变的实际行为与保留条件 |
| 准备 | 可审阅的 change brief、candidate 规则与相关验证命令 | 原 renderer 中的具体 source change |
| 验证 | 所执行层级的结果、未验分支和失败样例 | 指定 binary、实际 request 与使用结果 |
| 接入 | 研究依据与预期变化 | 原 selector、安装/激活授权、运行观察与恢复操作 |
| 回填 | 可复用的结论、版本边界和新的反例 | 私人机器事实/原始请求继续留 Git 外 |

本仓库不会为了一张总览图复制生产 settings、另建 Memory backend 或接管 channel 账号。实际配置修改与恢复的定位顺序见 [Runtime integration](runtime-integration.md)。同样，未来若某条配置规则已被采用，研究页必须记录采用位置和证据层级；“candidate 写完”不能悄悄变成“已经 live”。

## 现在可以操作到哪里

Atlas 的全景、合成回放、对照研究、来源查询和变更 brief 都使用本地材料。对照 plan 保存完整合成 fixture snapshot；`scripts/run_context_study.py` 复用 canonical 引擎重跑两组条件，报告事实与研究者声明的保留要求分开。来源轨迹的差异不能直接推出自然语义改善，也不能把 current 退出写成历史已删除。typed decisions 仍是独立的 shadow 实验，没有进入本次比较的后续 ledger。

它给出的验证集合是 [model.json](../workbench/model.json) 中有出处的人工关系判断，并非自动发现所有依赖的分析器。输入一个目标版本只为标明变更意图，不会获得兼容性认证。

后续的实质进展，以能回答上面四种完整问题为准：补齐某条链路缺失的 source/runtime 证据、修正已知假设、形成能交给原项目的具体改动。新的界面、更多文件或更多通过的测试，不单独构成进展。
