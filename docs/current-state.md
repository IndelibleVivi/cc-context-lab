# 当前研究状态

更新：2026-11-01（Asia/Singapore）。范围已扩展为 **Harness Context Engineering Lab**；Claude Code 是研究最深入的一条线。现有 repo / slug 仍为 `cc-context-lab`，`main` 管理 source，现有 remote 已核为 private。当前是**可使用的研究、离线实验和本地请求观察与案例工作台**；不是已部署的 context manager 或完整 persona/profile。

## 2026-11-01 日常 presentation candidate

新增 [Daily quiet](../experiments/daily-quiet/README.md)：canonical纯规则、standalone Mods接线、13项Node合成检查、三项native test-kit fixture及可重跑case。来源为已审原生话术片段的digest与project-authored变换，不收录原厂全文或私人context。规则不按CC版本开关；未知片段、新功能事实与schema保留，严格恢复资格继续由runtime owner独立管理。

Linux CC2.1.314/2.1.316分别通过native validation（含catalog warnings）和3项合成事件测试。上下文fixture必须让claudeMd与instructionFiles一致，才能判断保留追踪；故意不一致的输入被原生引擎撤去metadata，不能据此归因候选丢失。独立review指出全局空白归一化会改变未知示例，已改成保留所有非目标分隔符并加回归。

合成case真实调用纯规则与既有case引擎：6项结构要求PASS，真实resume、模型体验和交付3项NOT_ASSESSED；没有整体readiness结论。本节不声称runtime安装、provider请求或自然相处验收。当前仓库仍private、公开rights尚未选定；公开候选只包含authored source、synthetic fixtures和public-safe evidence。

## 当前方向与能力

初始 `cec2344` 已要求覆盖 system/tools/messages、compact/resume/subagent 和完整 owned-context；后来的伴侣语境扩展澄清了当下感、自动 recall、自主时间与经历承接的用途。不能把目标缩成 token 裁剪、局部提醒替换或工程 scheduler。整体结构见 [README 架构图](../README.md#架构与边界)，连续建设见 [development programme](development-programme.md)。

| 现在可使用的路径 | 已具备的结果与边界 |
| --- | --- |
| [研究库与版本依据](research-evidence.md) | 十六项公开上游、官方合同、逐项提醒映射和有界 source 阅读；日期/版本/覆盖分开记录，不自动升级 pin |
| [可复现 A/B 研究](../experiments/companion-input/STUDIES.md) | 固定完整合成 fixture snapshot，比较 trigger/placement/history，CLI 重跑、逐来源 current/history/排除/轮后轨迹、保存/恢复与固定 brief 附件；复用 canonical run_session |
| [本地请求观察](request-observation.md) | Anthropic Messages / OpenAI Responses 的 strict capture、完整 body/section 原值与未知参数、条件/位置比较、CLI 和 Atlas 请求观察视图、JSON/Markdown 与固定 brief 附件；默认只含合成示例 |
| [贯通阶段的 context case](context-cases.md) | 固定同一个问题/要求、合成 study snapshot、内嵌多阶段 captures 与显式比较；CLI 重跑、局部结构检查、失败/未评估、完整报告与固定 brief，阶段关联由研究者声明 |
| [CC candidate 与升级检查](maintenance.md#检查指定-cc-版本的-candidate) | 可审阅 source 和隔离的官方 offline checker；既往 2.1.289 验证、types 与一次 composition 观察保留 10/05 条件，本轮没有重跑 binary 或 runtime probe |

通用观察器按 wire format 读取，不承诺所有使用这些格式的 harness 兼容。同格式按 JSON pointer 比较位置，跨格式不自动配对。origin/lifecycle 保持 unknown，服务端历史/prompt 引用不展开；captured_request 是导入者声明，模型使用和外部交付仍为 NOT_ASSESSED。真实 capture 只通过显式 `--capture` 进入本机 ignored 或 Git 外的产物，不扫描 logs，也不进入 private remote。

## 本轮验证与可靠性

10/28 `python3 scripts/check_offline.py`：**197 项顶层/Node cases 与四项 JS syntax 通过**。本轮新增 case/CLI 22、case→Atlas 7、case presenter 9；既有 159 项继续通过。没有调用 CC binary、第三方 checkout、网络或真实 provider；此前版本证据保留原观察日期。

case 的 pointer 检查分开 present / 明确的最终缺失 / 遍历阻断；null 与缺失不同，错索引、缺祖先或缺 capture 不给 absence 假阳性。字面的 `#` / `*`、`~0/~1`、纯空白子串和极大数组索引有回归。原值与报告沿用 Python canonical 文本；不安全整数不会进入关联 study 的启动恢复、case 恢复按钮或可编辑 scenario registry；普通 study 视图会明确显示独立情境提示。报告使用随 payload 调整的 code fence，保留原始 backticks。输入/输出 alias、坏输入、输出限制和旧报告保留继续受共享 writer 保护。

实际完成浏览器 case JSON → CLI → case/report → builder --case → 重开、阶段原值、FAIL/NOT_ASSESSED 筛选、显式请求比较、关联 study 恢复/编辑与固定 brief 下载。最终 JSON/Markdown 与 canonical replay 一致，brief 包含同次固定报告。示例刻意含 1 项 requirement FAIL 和 3 项 NOT_ASSESSED，CLI 返回 1 并生成报告；不把预期失败写成全部条件通过。

另用合成跨格式阶段和 `9007199254740993` 检查条件变化、不自动配对、未展开 previous_response_id、期望/原值/下载保真与 unsafe study restore 拒绝。1440×1100 / 390×844 七视图无页面横向溢出，console 未见应用错误，README Mermaid 已渲染核对。浏览器证据来自 loopback 预览，不声称 file URL 或真实 harness 验收。10/25 的 studies / 观察器回归与 UI-only 输入泄漏修复仍保留，详细历史见 [研究证据](research-evidence.md)。

## 尚未验证与下一集成点

- 新观察器尚未以真实 harness capture 验收 runtime provenance；请求正文本身也不足以证明真实 origin、隐藏 context 或模型正确使用。
- 新会话、compact、resume、subagent、自主轮次和 channel 的完整真实请求与自然语义效果仍缺；现实聊天结束/占用的判定也未解决。
- typed decisions 目前只有 scripted shadow replay 和 PREPARED_NOT_SENT 请求，没有真实 response adapter、推理、usage/延迟或语义增益证据。
- 日常本机/VPS 安装、Mods 启用与当前生产状态没有在本轮核实。10/05 的独立 2.1.289 artifact 与零 provider 请求的 composition 探针不能代替这些事实。
- 未逐份深读的 named prompt/inline、未审目标 symbols、其它独立归档与多轮连续性分支保留各专题的覆盖限制；入口见 [研究证据](research-evidence.md)。

当前 case 已连接研究问题、条件、阶段输入与结构结果；下一主线沿现有 capture 入口，将**同一个研究问题、条件和保留要求**带到指定 build/入口/candidate 的真实观察，再交回原 runtime 的接入、恢复和自然使用回填。主 system/tools/reminders、ambient、自动 recall、自主活动、channel 与 compact/Forge 始终保留在完整目标内；不另造 scheduler、Memory backend 或自动生产控制层。具体接点见 [Context DevOps](context-devops.md) 与 programme。

本轮 source/test/docs 可正常 commit/push 至现有 private remote；私人 continuity、身份、真实配置/capture/transcript 和 cache 留在 Git 外。没有新增 CC 探针、真实模型推理、scheduler、消息发送、安装、VPS 或部署操作，也未公开发布或选择公开 license。
