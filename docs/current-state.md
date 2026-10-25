# 当前研究状态

更新：2026-10-25（Asia/Singapore）。范围已扩展为 **Harness Context Engineering Lab**；Claude Code 是研究最深入的一条线。现有 repo / slug 仍为 `cc-context-lab`，`main` 管理 source，现有 remote 已核为 private。当前是**可使用的研究、离线实验和本地请求观察工作台**；不是已部署的 context manager 或完整 persona/profile。

## 当前方向与能力

初始 `cec2344` 已要求覆盖 system/tools/messages、compact/resume/subagent 和完整 owned-context；后来的伴侣语境扩展澄清了当下感、自动 recall、自主时间与经历承接的用途。不能把目标缩成 token 裁剪、局部提醒替换或工程 scheduler。整体结构见 [README 架构图](../README.md#架构与边界)，连续建设见 [development programme](development-programme.md)。

| 现在可使用的路径 | 已具备的结果与边界 |
| --- | --- |
| [研究库与版本依据](research-evidence.md) | 十六项公开上游、官方合同、逐项提醒映射和有界 source 阅读；日期/版本/覆盖分开记录，不自动升级 pin |
| [可复现 A/B 研究](../experiments/companion-input/STUDIES.md) | 固定完整合成 fixture snapshot，比较 trigger/placement/history，CLI 重跑、逐来源 current/history/排除/轮后轨迹、保存/恢复与固定 brief 附件；复用 canonical run_session |
| [本地请求观察](request-observation.md) | Anthropic Messages / OpenAI Responses 的 strict capture、完整 body/section 原值与未知参数、条件/位置比较、CLI 和 Atlas 第六视图、JSON/Markdown 与固定 brief 附件；默认只含合成示例 |
| [CC candidate 与升级检查](maintenance.md#检查指定-cc-版本的-candidate) | 可审阅 source 和隔离的官方 offline checker；既往 2.1.289 验证、types 与一次 composition 观察保留 10/05 条件，本轮没有重跑 binary 或 runtime probe |

通用观察器按 wire format 读取，不承诺所有使用这些格式的 harness 兼容。同格式按 JSON pointer 比较位置，跨格式不自动配对。origin/lifecycle 保持 unknown，服务端历史/prompt 引用不展开；captured_request 是导入者声明，模型使用和外部交付仍为 NOT_ASSESSED。真实 capture 只通过显式 `--capture` 进入本机 ignored 或 Git 外的产物，不扫描 logs，也不进入 private remote。

## 本轮验证与可靠性

`python3 scripts/check_offline.py`：**159 项顶层/Node cases 与三项 JS syntax 通过**，覆盖既有引擎、typed decision 合同、study/CLI、Atlas、candidate、checker、请求准备，以及新观察器与报告写入。没有调用 CC binary、第三方 checkout、网络或真实 provider；各 suite 计数与条件见 [证据记录](research-evidence.md#2026-10-25方向校准与验证覆盖)。

已修复 UI-only 环境/消息预览流入 current/history、错误导入损害工作、输入/输出 alias 和异常编码破坏旧报告等问题。两个报告 CLI 与 Atlas 共用预编码/预检/暂存后逐文件 atomic replace；不是多文件事务。观察显示、搜索与下载使用 Python canonical 文本，保护超过 JS 安全范围的整数。

浏览器实际完成 study 保存→CLI→builder→恢复→来源/回放→brief，以及新观察页的同格式/跨格式、schema 原值、搜索空结果/恢复、未展开引用、下载和固定附件。JSON/Markdown 下载与 canonical 文本相等，brief 保留带入时的比较。显式两份大整数合成 capture 的 CLI/Atlas/浏览器下载一致，仅包含指定文件并默认打开观察页。1440×1100 与 390×844 六视图无页面横向溢出，窄屏观察为单列，console 未见应用错误。README Mermaid 已本地渲染核对，未增加 runtime dependency；上述浏览器证据来自 loopback 预览，不声称 file URL 或真实 harness 验收。

## 尚未验证与下一集成点

- 新观察器尚未以真实 harness capture 验收 runtime provenance；请求正文本身也不足以证明真实 origin、隐藏 context 或模型正确使用。
- 新会话、compact、resume、subagent、自主轮次和 channel 的完整真实请求与自然语义效果仍缺；现实聊天结束/占用的判定也未解决。
- typed decisions 目前只有 scripted shadow replay 和 PREPARED_NOT_SENT 请求，没有真实 response adapter、推理、usage/延迟或语义增益证据。
- 日常本机/VPS 安装、Mods 启用与当前生产状态没有在本轮核实。10/05 的独立 2.1.289 artifact 与零 provider 请求的 composition 探针不能代替这些事实。
- 未逐份深读的 named prompt/inline、未审目标 symbols、其它独立归档与多轮连续性分支保留各专题的覆盖限制；入口见 [研究证据](research-evidence.md)。

下一主线沿现有 capture 入口，将**同一个研究问题、条件和保留要求**带到指定 build/入口/candidate 的真实观察，再交回原 runtime 的接入、恢复和自然使用回填。主 system/tools/reminders、ambient、自动 recall、自主活动、channel 与 compact/Forge 始终保留在完整目标内；不另造 scheduler、Memory backend 或自动生产控制层。具体接点见 [Context DevOps](context-devops.md) 与 programme。

本轮 source/test/docs 可正常 commit/push 至现有 private remote；私人 continuity、身份、真实配置/capture/transcript 和 cache 留在 Git 外。没有新增 CC 探针、真实模型推理、scheduler、消息发送、安装、VPS 或部署操作，也未公开发布或选择公开 license。
