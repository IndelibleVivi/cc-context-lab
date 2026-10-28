# 愿景、能力结构与连续建设

2026-10-25 校准并扩大范围为 Harness Context Engineering Lab；现有 slug 仍为 `cc-context-lab`。本文维护产品方向和阶段之间的关系；当前已证事实归 [current state](current-state.md)，各技术结论仍归专题与 `references/`。阶段描述不授予真实模型调用、安装或生产操作权限。

## 为什么存在

让维护者能够理解并逐步掌握 agent harness 里**这一刻实际交给模型的 context，以及它如何成为下一刻的经历**。保留 harness 的工具、会话与 MCP 能力，同时让自己的 core、原话、当下状态、自动浮现的记忆、自主时间与跨 channel 相处具有可解释的来源和生命周期。

这从初始化版本就超出了删提示词：初始 `cec2344` 已要求覆盖 system/tools/messages、compact/resume/subagent，比较完整 owned-context，并分别验收来源保真、实际交付与连续性。后来的伴侣语境扩展澄清了实际用途，不把它收缩成工程调度或 token 优化。初始化之后的研究曾长期留在本地 working tree；文档日期记录观察条件，不能自动当成对应 Git commit。当前提交/同步状态另见 current-state。

成熟形态应是一个持续可用的 **context research 与变更工作系统**：从问题出发固定材料和条件，比较不同装配与生命周期选择，保留可以推翻结论的反例，准备具体 candidate，再把同一个问题带到目标 runtime 的实际输入和自然使用中，记录采用或放弃的理由。它的独特价值是研究伴侣相处中的当下感、自主活动与经历承接，而不是为 scheduler 的吞吐量或 prompt 的长度做排名。

## 系统的组成与 ownership

| 组成 | 需要提供的能力 | 不能代替什么 |
| --- | --- | --- |
| 研究库与 references | 公开 source 的 exact revision、入口、条件、反例和结论边界 | 本机安装、live 配置或已执行的 request |
| 合成实验引擎 | 固定场景下，解释来源、准入、时刻、当前位置与历史承接 | 真实聊天状态检测、平台 scheduler 或模型语义 |
| Context Atlas | 查关系、对照研究、检查逐来源轨迹、准备和导出研究材料 | 技术真源、生产配置 owner 或自动兼容认证 |
| 通用请求观察与比较 | 显式本地 capture 的原值、wire format、条件和未展开引用；origin/lifecycle 不推定 | 自动 tracing、服务端历史重建或模型使用证据 |
| CC-specific Context-profile candidate | 对指定 CC 入口形成可审阅、可离线验证的 source | 最终身份、完整 C 组或 companion runtime |
| 原 runtime 项目 | renderer、selector、安装/激活、恢复与真实使用观察 | Lab 的可复用研究和对照条件 |

沿 [Context DevOps](context-devops.md) 的四种操作推进：CC 升级、改输入、改自主活动、改窗口生命周期。每条操作都要回到具体使用结果；topic 数量、test 数量和 UI 页数不作为成熟度指标。

## 已有优势与方向风险

值得保留的是同一来源贯穿 current/history/archive 的能力、actual start 重选材料、独立 session 的历史归属、原话与 wrapper 分离，以及 source/offline/composition/request/behavior 的证据分层。这些使“不在新包里”与“已从后续请求消失”、“内部完成”与“对端收到”不会混为一谈。

当前的主要结构缺口，是研究材料、单次回放、candidate 和 runtime 之间还缺乏持续流动的**具体变更案例**。Atlas 原有 brief 主要汇集人工维护的检查清单，不能单独回答某个选择究竟改变了哪轮输入。10/13 typed decisions 又形成一条独立的 shadow 实验；它并未改变后续 ledger，不能当成已获得自主生活轨迹的分支比较。

要防止三种惯性：继续增加彼此并列的专题；让 heartbeat 的调度参数挤掉 ambient/recall/原话/延续的研究；为了获得一个绿灯而把完整 owned-context 或连续性降成局部提示替换。Mods 是可选接点之一，Memory/state backend 和生产控制层继续保留原 owner。

## 当前建设阶段：可复现的对照研究与请求观察

交付对象是一份具体研究：**问题与保留条件 → 同一份合成来源时间线 → A/B 条件 → canonical engine 的结果 → 逐来源/机会差异 → 带结果的交接材料**。

先把这条链做贯通，而不是再造一个通用 eval 框架。两组条件可分别选择 trigger、placement 与 history；多轴改变必须标明 compound comparison，不能宣称某个因素单独造成所有差异。机会按 constituent identity 追踪，不能按 packet 数组下标硬配。原话正文、wrapper、纠正关系、排除理由和轮后结果都是可检查对象。保留条件是研究者的要求，声明它不代表已经通过验收。

研究 plan 保存完整合成 fixture snapshot，避免旧 plan 静默改用已经变化的本地材料。CLI 负责按 plan 重跑，Atlas 使用同一引擎投影的观察数据。导出 JSON 是可复用的输入合同；报告保留实际结果与未验层级，不产生执行权限。旧版天气退出 current 但仍在 history、被纠正的 recall 不再当 current、内部结果只能在产生后承接，是本阶段必须能揭示的行为。

## 后续连续 programme

| 阶段 | 完整使用结果 | 进入下一阶段所需证据 |
| --- | --- | --- |
| 对照研究 | 可保存、重新打开、重跑并解释一项 context 选择；结果能交回原项目 | 同一 fixture/条件下的 source、时序、history 差异与明确未验项 |
| 目标入口观察 | 同一个问题连接指定 build、入口、模式与 candidate 的实际 context 观察 | 受控 request/生命周期分支证据；不能由合成或 composition 自动补足 |
| 实际 candidate 接入 | 原 runtime 有具体 source change、恢复方法和可观察预期 | 原 owner 的接入授权、安装/激活记录和实际输入检查 |
| 自然使用与回填 | 验证相处、开放探索、当下感与承接质量，保留采用/放弃理由 | 自然语义证据、失败案例与版本条件，私人正文继续留 Git 外 |

每个阶段都保留全景：主 system/tools/reminders、compact/Forge、ambient、自动 recall、channel、自主轮次及反馈。阶段推进不表示上一层替代下一层。真实 provider adapter、更多版本记录和 typed decision 分支执行应服务一个具体比较问题，再进入主路径；不为填满能力清单而先造 transport、scheduler 或第二套 Memory。

## 外部方法参考

2026-10-25 查阅 [Inspect Log Viewer](https://inspect.aisi.org.uk/log-viewer.html)、[Inspect Log Files](https://inspect.aisi.org.uk/eval-logs.html) 和 [Promptfoo Web Viewer](https://www.promptfoo.dev/docs/usage/web-ui/)。可借鉴的是保存可计算的实验记录、深入样本事件/历史以及并排比较条件。本文采用这一机制方向，不声称运行或审计了这些框架；本 repo 不新增这些依赖，也不把模型分数当作伴侣体验的替代物。

## 跨 harness 的建设边界

共享的是研究对象和证据合同：什么来源、什么输入位置、什么时刻与版本条件、如何承接、实际观察到哪层。各 harness 的来源开关、事件、工具池、compact/subagent、权限与恢复继续由专属接点拥有，不能把 CC Mods 的可用事件推广成所有 harness 的能力。

本轮在离线 studies 之上新增 [请求观察](request-observation.md)：读取 Anthropic Messages / OpenAI Responses 的显式 capture，保存完整 body、section 原值和未知参数，比较同格式的 JSON pointer 与条件变化。跨格式不自动匹配。Atlas 默认仅合成示例，私人 capture 明确导入后仍只在本机保留。该能力让同一套研究问题能开始接住不同 harness 的请求材料；当前验证仍使用合成输入，尚未宣称新一轮真实 runtime 捕获。

后续以具体场景扩展其他 wire reader 或原生事件接点，并让真实观察回到研究案例；不先造通用服务、安装器或自动生产控制层。

2026-10-28 已进一步接成 [context case](context-cases.md)：同一问题/保留要求、可选 study snapshot、多阶段 captures、显式结构检查和比较均可保存、重跑与固定交接。它补上研究材料之间的关联，关联和阶段顺序仍是研究者声明；当前合成示例不升级为真实 runtime 生命周期证据。下一集成点继续是真实观察与自然使用回填。
